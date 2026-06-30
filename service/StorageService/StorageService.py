import io
import logging
import uuid
from datetime import timedelta
from typing import Optional

logger = logging.getLogger(__name__)

from minio import S3Error
from minio.commonconfig import CopySource, Tags

from core.config.MinioConfig import get_minio_client
from core.response.ErrorStatus import ErrorStatus
from domain.model.StorageBucket import StorageBucket
from domain.model.StorageResource import StorageResource
from extensions import db
from web.dto.StorageRequestDTO import CreateBucketRequestDTO, CopyObjectRequestDTO, SetObjectTagsRequestDTO
from web.dto.StorageResponseDTO import (
    BucketResponseDTO,
    ObjectInfoDTO,
    PresignedUrlDTO,
    StatObjectDTO,
    UploadResultDTO,
)


class StorageException(Exception):
    def __init__(self, error_status):
        self.error_status = error_status
        super().__init__(error_status.message)


def _minio():
    return get_minio_client()


# ── Bucket Operations ─────────────────────────────────────────────────────────

def create_bucket(dto: CreateBucketRequestDTO, creator_id: str) -> BucketResponseDTO:
    client = _minio()
    if StorageBucket.query.filter_by(bucket_name=dto.bucket_name).first():
        raise StorageException(ErrorStatus.STORAGE_BUCKET_ALREADY_EXISTS)

    try:
        if not client.bucket_exists(dto.bucket_name):
            client.make_bucket(dto.bucket_name)
    except S3Error as e:
        raise StorageException(ErrorStatus.STORAGE_OPERATION_FAILED) from e

    bucket = StorageBucket(
        bucket_id=str(uuid.uuid4()),
        bucket_name=dto.bucket_name,
        created_by=creator_id,
    )
    db.session.add(bucket)
    db.session.commit()
    return _bucket_to_dto(bucket)


def list_buckets() -> list[BucketResponseDTO]:
    buckets = StorageBucket.query.order_by(StorageBucket.created_at).all()
    return [_bucket_to_dto(b) for b in buckets]


def get_bucket(bucket_name: str) -> BucketResponseDTO:
    bucket = _get_bucket_or_raise(bucket_name)
    return _bucket_to_dto(bucket)


def delete_bucket(bucket_name: str, force: bool = False) -> None:
    bucket = _get_bucket_or_raise(bucket_name)
    client = _minio()

    if not force:
        objects = list(client.list_objects(bucket_name, recursive=True))
        if objects:
            raise StorageException(ErrorStatus.STORAGE_BUCKET_NOT_EMPTY)

    try:
        if force:
            for obj in client.list_objects(bucket_name, recursive=True):
                client.remove_object(bucket_name, obj.object_name)
        client.remove_bucket(bucket_name)
    except S3Error as e:
        raise StorageException(ErrorStatus.STORAGE_OPERATION_FAILED) from e

    db.session.delete(bucket)
    db.session.commit()


# ── Object Operations ─────────────────────────────────────────────────────────

def list_objects(bucket_name: str, prefix: str = '', recursive: bool = False) -> list[ObjectInfoDTO]:
    _get_bucket_or_raise(bucket_name)
    client = _minio()
    try:
        # list()로 eager 평가 — generator 반복 중 발생하는 S3Error도 여기서 잡힘
        raw = list(client.list_objects(
            bucket_name,
            prefix=prefix or None,   # 빈 문자열 대신 None 전달
            recursive=recursive,
        ))
    except S3Error as e:
        logger.error("MinIO list_objects 실패 | bucket=%s prefix=%r | code=%s message=%s",
                     bucket_name, prefix, e.code, getattr(e, 'message', str(e)))
        if e.code == 'NoSuchBucket':
            raise StorageException(ErrorStatus.STORAGE_BUCKET_NOT_FOUND) from e
        raise StorageException(ErrorStatus.STORAGE_OPERATION_FAILED) from e
    except Exception as e:
        logger.error("MinIO list_objects 예외 | bucket=%s prefix=%r | %s: %s",
                     bucket_name, prefix, type(e).__name__, e)
        raise StorageException(ErrorStatus.STORAGE_OPERATION_FAILED) from e

    return [
        ObjectInfoDTO(
            object_name=obj.object_name,
            size=obj.size or 0,
            etag=obj.etag or '',
            last_modified=obj.last_modified,
            is_dir=obj.is_dir,
        )
        for obj in raw
    ]


def upload_object(bucket_name: str, object_name: str, data: bytes,
                  content_type: str, owner_id: str) -> UploadResultDTO:
    _get_bucket_or_raise(bucket_name)
    client = _minio()
    stream = io.BytesIO(data)
    size = len(data)

    try:
        result = client.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            data=stream,
            length=size,
            content_type=content_type,
        )
    except S3Error as e:
        raise StorageException(ErrorStatus.STORAGE_OPERATION_FAILED) from e

    resource = StorageResource.query.filter_by(
        bucket_name=bucket_name,
        s3_key=object_name,
        is_deleted=False,
    ).first()

    if resource:
        resource.resource_name = object_name.split('/')[-1]
        resource.owner_id = owner_id
    else:
        resource = StorageResource(
            resource_id=str(uuid.uuid4()),
            bucket_name=bucket_name,
            resource_name=object_name.split('/')[-1],
            s3_key=object_name,
            owner_id=owner_id,
        )
        db.session.add(resource)
    db.session.commit()

    return UploadResultDTO(
        bucket_name=bucket_name,
        object_name=object_name,
        etag=result.etag or '',
        size=size,
    )


def stat_object(bucket_name: str, object_name: str) -> StatObjectDTO:
    _get_bucket_or_raise(bucket_name)
    client = _minio()
    try:
        stat = client.stat_object(bucket_name, object_name)
    except S3Error:
        raise StorageException(ErrorStatus.STORAGE_OBJECT_NOT_FOUND)

    return StatObjectDTO(
        object_name=stat.object_name,
        size=stat.size,
        etag=stat.etag or '',
        last_modified=stat.last_modified,
        content_type=stat.content_type or 'application/octet-stream',
        metadata=dict(stat.metadata or {}),
    )


def presigned_download_url(bucket_name: str, object_name: str,
                           expires_seconds: int = 3600) -> PresignedUrlDTO:
    _get_bucket_or_raise(bucket_name)
    client = _minio()
    try:
        url = client.presigned_get_object(
            bucket_name=bucket_name,
            object_name=object_name,
            expires=timedelta(seconds=expires_seconds),
        )
    except S3Error:
        raise StorageException(ErrorStatus.STORAGE_OBJECT_NOT_FOUND)

    return PresignedUrlDTO(url=url, expires_in=expires_seconds)


def presigned_share_url(bucket_name: str, object_name: str,
                        expires_seconds: int = 43200) -> PresignedUrlDTO:
    _get_bucket_or_raise(bucket_name)
    client = _minio()
    try:
        url = client.presigned_get_object(
            bucket_name=bucket_name,
            object_name=object_name,
            expires=timedelta(seconds=expires_seconds),
        )
    except S3Error:
        raise StorageException(ErrorStatus.STORAGE_OBJECT_NOT_FOUND)

    return PresignedUrlDTO(url=url, expires_in=expires_seconds)


def delete_object(bucket_name: str, object_name: str) -> None:
    _get_bucket_or_raise(bucket_name)
    client = _minio()
    try:
        client.stat_object(bucket_name, object_name)
    except S3Error:
        raise StorageException(ErrorStatus.STORAGE_OBJECT_NOT_FOUND)

    try:
        client.remove_object(bucket_name, object_name)
    except S3Error as e:
        raise StorageException(ErrorStatus.STORAGE_OPERATION_FAILED) from e

    resource = StorageResource.query.filter_by(
        bucket_name=bucket_name,
        s3_key=object_name,
        is_deleted=False,
    ).first()
    if resource:
        resource.is_deleted = True
        db.session.commit()


def copy_object(bucket_name: str, dto: CopyObjectRequestDTO) -> None:
    _get_bucket_or_raise(bucket_name)
    _get_bucket_or_raise(dto.dest_bucket)
    client = _minio()
    try:
        client.copy_object(
            bucket_name=dto.dest_bucket,
            object_name=dto.dest_object,
            source=CopySource(bucket_name, dto.source_object),
        )
    except S3Error as e:
        if e.code == 'NoSuchKey':
            raise StorageException(ErrorStatus.STORAGE_OBJECT_NOT_FOUND)
        raise StorageException(ErrorStatus.STORAGE_OPERATION_FAILED) from e


# ── Object Tags ───────────────────────────────────────────────────────────────

def get_object_tags(bucket_name: str, object_name: str) -> dict:
    _get_bucket_or_raise(bucket_name)
    client = _minio()
    try:
        tags = client.get_object_tags(bucket_name, object_name)
        return dict(tags) if tags else {}
    except S3Error as e:
        if e.code == 'NoSuchKey':
            raise StorageException(ErrorStatus.STORAGE_OBJECT_NOT_FOUND)
        raise StorageException(ErrorStatus.STORAGE_OPERATION_FAILED) from e


def set_object_tags(bucket_name: str, dto: SetObjectTagsRequestDTO) -> None:
    _get_bucket_or_raise(bucket_name)
    client = _minio()
    try:
        tags = Tags.new_object_tags()
        for k, v in dto.tags.items():
            tags[k] = v
        client.set_object_tags(bucket_name, dto.object_name, tags)
    except S3Error as e:
        if e.code == 'NoSuchKey':
            raise StorageException(ErrorStatus.STORAGE_OBJECT_NOT_FOUND)
        raise StorageException(ErrorStatus.STORAGE_OPERATION_FAILED) from e


def delete_object_tags(bucket_name: str, object_name: str) -> None:
    _get_bucket_or_raise(bucket_name)
    client = _minio()
    try:
        client.delete_object_tags(bucket_name, object_name)
    except S3Error as e:
        if e.code == 'NoSuchKey':
            raise StorageException(ErrorStatus.STORAGE_OBJECT_NOT_FOUND)
        raise StorageException(ErrorStatus.STORAGE_OPERATION_FAILED) from e


# ── Private helpers ───────────────────────────────────────────────────────────

def _get_bucket_or_raise(bucket_name: str) -> StorageBucket:
    bucket = StorageBucket.query.filter_by(bucket_name=bucket_name).first()
    if not bucket:
        raise StorageException(ErrorStatus.STORAGE_BUCKET_NOT_FOUND)
    return bucket


def _bucket_to_dto(bucket: StorageBucket) -> BucketResponseDTO:
    return BucketResponseDTO(
        bucket_id=bucket.bucket_id,
        bucket_name=bucket.bucket_name,
        created_by=bucket.created_by,
        created_at=bucket.created_at,
    )
