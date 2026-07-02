from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from core.rbac.RBACUtils import storage_required, get_accessible_object_keys
from core.response.ApiResponse import ApiResponse
from core.response.ErrorStatus import ErrorStatus
from core.response.SuccessStatus import SuccessStatus
from domain.model.Member import Member
from domain.model.StorageBucket import StorageBucket
from domain.model.StorageResource import StorageResource
from service.StorageService.StorageService import (
    StorageException,
    MAX_FILE_SIZE,
    create_bucket,
    list_buckets,
    get_bucket,
    delete_bucket,
    list_objects,
    upload_object,
    stat_object,
    presigned_download_url,
    presigned_share_url,
    delete_object,
    delete_folder,
    copy_object,
    get_object_tags,
    set_object_tags,
    delete_object_tags,
)
from web.dto.StorageRequestDTO import (
    CreateBucketRequestDTO,
    CopyObjectRequestDTO,
    SetObjectTagsRequestDTO,
)

storage_bp = Blueprint('storage', __name__, url_prefix='/api/storage')


def _current_member_id() -> str:
    member = Member.query.filter_by(account_id=get_jwt_identity()).first()
    return member.id if member else get_jwt_identity()


def _handle(fn):
    try:
        return fn()
    except StorageException as e:
        return ApiResponse.on_failure(e.error_status)
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, str(e))
    except Exception as e:
        return ApiResponse.on_failure(ErrorStatus._INTERNAL_SERVER_ERROR, str(e))


# ── 버킷/오브젝트 목록 (권한 할당 UI용) ──────────────────────────────────────

@storage_bp.route('/buckets-meta', methods=['GET'])
@jwt_required()
@storage_required('READ')
def api_list_buckets_meta():
    """버킷 목록 (bucket_id 포함) — STORAGE permission 생성 시 BUCKET 선택용."""
    buckets = StorageBucket.query.order_by(StorageBucket.created_at).all()
    result = [
        {"bucketId": b.bucket_id, "bucketName": b.bucket_name, "createdAt": b.created_at.isoformat()}
        for b in buckets
    ]
    return ApiResponse.on_success(SuccessStatus.STORAGE_BUCKET_READ, result)


@storage_bp.route('/resources', methods=['GET'])
@jwt_required()
@storage_required('READ')
def api_list_db_resources():
    """DB에 등록된 오브젝트 목록 (resource_id 포함) — STORAGE permission 생성 시 OBJECT 선택용."""
    bucket_name = request.args.get('bucketName')
    q = StorageResource.query.filter_by(is_deleted=False)
    if bucket_name:
        q = q.filter_by(bucket_name=bucket_name)
    resources = q.order_by(StorageResource.created_at).all()
    result = [
        {
            "resourceId":   r.resource_id,
            "bucketName":   r.bucket_name,
            "resourceName": r.resource_name,
            "s3Key":        r.s3_key,
            "createdAt":    r.created_at.isoformat(),
        }
        for r in resources
    ]
    return ApiResponse.on_success(SuccessStatus.STORAGE_OBJECT_LIST, result)


# ── Bucket endpoints ──────────────────────────────────────────────────────────

@storage_bp.route('/buckets', methods=['POST'])
@jwt_required()
@storage_required('MANAGE')
def api_create_bucket():
    body = request.get_json(silent=True) or {}
    def work():
        dto = CreateBucketRequestDTO(bucket_name=body.get('bucketName', '').strip())
        result = create_bucket(dto, _current_member_id())
        return ApiResponse.on_success(SuccessStatus.STORAGE_BUCKET_CREATE, result)
    return _handle(work)


@storage_bp.route('/buckets', methods=['GET'])
@jwt_required()
@storage_required('READ')
def api_list_buckets():
    def work():
        result = list_buckets()
        return ApiResponse.on_success(SuccessStatus.STORAGE_BUCKET_READ, result)
    return _handle(work)


@storage_bp.route('/buckets/<bucket_name>', methods=['GET'])
@jwt_required()
@storage_required('READ')
def api_get_bucket(bucket_name: str):
    def work():
        result = get_bucket(bucket_name)
        return ApiResponse.on_success(SuccessStatus.STORAGE_BUCKET_READ, result)
    return _handle(work)


@storage_bp.route('/buckets/<bucket_name>', methods=['DELETE'])
@jwt_required()
@storage_required('MANAGE')
def api_delete_bucket(bucket_name: str):
    force = request.args.get('force', 'false').lower() == 'true'
    def work():
        delete_bucket(bucket_name, force=force)
        return ApiResponse.on_success(SuccessStatus.STORAGE_BUCKET_DELETE)
    return _handle(work)


# ── Object list / upload / stat / download URL / delete / copy ────────────────

@storage_bp.route('/buckets/<bucket_name>/objects', methods=['GET'])
@jwt_required()
@storage_required('READ')
def api_list_objects(bucket_name: str):
    prefix    = request.args.get('prefix', '')
    recursive = request.args.get('recursive', 'false').lower() == 'true'
    def work():
        result = list_objects(bucket_name, prefix=prefix, recursive=recursive)

        # OBJECT 레벨 권한이면 허용된 오브젝트만 필터링
        # None → 버킷 전체 허용, list → 해당 s3_key만 허용
        allowed_keys = get_accessible_object_keys(bucket_name)
        if allowed_keys is not None:
            allowed_set = set(allowed_keys)
            # 디렉터리 항목(가상 폴더)은 내비게이션용으로 유지,
            # 실제 파일은 허용된 것만 표시
            result = [
                obj for obj in result
                if obj.is_dir or obj.object_name in allowed_set
            ]

        return ApiResponse.on_success(SuccessStatus.STORAGE_OBJECT_LIST, result)
    return _handle(work)


@storage_bp.route('/buckets/<bucket_name>/objects', methods=['POST'])
@jwt_required()
@storage_required('UPLOAD')
def api_upload_object(bucket_name: str):
    def work():
        if 'file' not in request.files:
            return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "file 필드가 없습니다.")
        file = request.files['file']
        # 전체 읽기 전에 크기부터 확인 (초과 시 메모리에 올리지 않고 즉시 거부)
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        if file_size > MAX_FILE_SIZE:
            return ApiResponse.on_failure(ErrorStatus.STORAGE_FILE_TOO_LARGE)
        object_name = request.form.get('objectName') or file.filename
        content_type = file.content_type or 'application/octet-stream'
        data = file.read()
        result = upload_object(bucket_name, object_name, data, content_type, _current_member_id())
        return ApiResponse.on_success(SuccessStatus.STORAGE_OBJECT_UPLOAD, result)
    return _handle(work)


@storage_bp.route('/buckets/<bucket_name>/objects/stat', methods=['GET'])
@jwt_required()
@storage_required('READ')
def api_stat_object(bucket_name: str):
    object_name = request.args.get('objectName', '')
    def work():
        if not object_name:
            return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "objectName 쿼리 파라미터가 필요합니다.")
        result = stat_object(bucket_name, object_name)
        return ApiResponse.on_success(SuccessStatus.STORAGE_OBJECT_STAT, result)
    return _handle(work)


@storage_bp.route('/buckets/<bucket_name>/objects/download-url', methods=['GET'])
@jwt_required()
@storage_required('DOWNLOAD')
def api_presigned_url(bucket_name: str):
    object_name = request.args.get('objectName', '')
    expires = int(request.args.get('expires', 3600))
    def work():
        if not object_name:
            return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "objectName 쿼리 파라미터가 필요합니다.")
        result = presigned_download_url(bucket_name, object_name, expires_seconds=expires)
        return ApiResponse.on_success(SuccessStatus.STORAGE_OBJECT_URL, result)
    return _handle(work)


@storage_bp.route('/buckets/<bucket_name>/objects/share-url', methods=['GET'])
@jwt_required()
@storage_required('SHARE')
def api_share_url(bucket_name: str):
    object_name = request.args.get('objectName', '')
    days    = max(0, int(request.args.get('days',    0)))
    hours   = max(0, int(request.args.get('hours',  12)))
    minutes = max(0, int(request.args.get('minutes', 0)))
    expires = days * 86400 + hours * 3600 + minutes * 60
    if expires <= 0:
        expires = 43200
    def work():
        if not object_name:
            return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "objectName 쿼리 파라미터가 필요합니다.")
        result = presigned_share_url(bucket_name, object_name, expires_seconds=expires)
        return ApiResponse.on_success(SuccessStatus.STORAGE_OBJECT_SHARE_URL, result)
    return _handle(work)


@storage_bp.route('/buckets/<bucket_name>/objects', methods=['DELETE'])
@jwt_required()
@storage_required('DELETE')
def api_delete_object(bucket_name: str):
    object_name = request.args.get('objectName', '')
    def work():
        if not object_name:
            return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "objectName 쿼리 파라미터가 필요합니다.")
        delete_object(bucket_name, object_name)
        return ApiResponse.on_success(SuccessStatus.STORAGE_OBJECT_DELETE)
    return _handle(work)


@storage_bp.route('/buckets/<bucket_name>/folders', methods=['DELETE'])
@jwt_required()
@storage_required('DELETE')
def api_delete_folder(bucket_name: str):
    prefix = request.args.get('prefix', '')
    def work():
        if not prefix:
            return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "prefix 쿼리 파라미터가 필요합니다.")
        delete_folder(bucket_name, prefix)
        return ApiResponse.on_success(SuccessStatus.STORAGE_FOLDER_DELETE)
    return _handle(work)


@storage_bp.route('/buckets/<bucket_name>/objects/copy', methods=['POST'])
@jwt_required()
@storage_required('MANAGE')
def api_copy_object(bucket_name: str):
    body = request.get_json(silent=True) or {}
    def work():
        dto = CopyObjectRequestDTO(
            source_object=body.get('sourceObject', ''),
            dest_bucket=body.get('destBucket', ''),
            dest_object=body.get('destObject', ''),
        )
        copy_object(bucket_name, dto)
        return ApiResponse.on_success(SuccessStatus.STORAGE_OBJECT_COPY)
    return _handle(work)


# ── Object Tags ───────────────────────────────────────────────────────────────

@storage_bp.route('/buckets/<bucket_name>/objects/tags', methods=['GET'])
@jwt_required()
@storage_required('READ')
def api_get_tags(bucket_name: str):
    object_name = request.args.get('objectName', '')
    def work():
        if not object_name:
            return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "objectName 쿼리 파라미터가 필요합니다.")
        result = get_object_tags(bucket_name, object_name)
        return ApiResponse.on_success(SuccessStatus.STORAGE_OBJECT_TAGS_GET, result)
    return _handle(work)


@storage_bp.route('/buckets/<bucket_name>/objects/tags', methods=['PUT'])
@jwt_required()
@storage_required('MANAGE')
def api_set_tags(bucket_name: str):
    body = request.get_json(silent=True) or {}
    def work():
        dto = SetObjectTagsRequestDTO(
            object_name=body.get('objectName', ''),
            tags=body.get('tags', {}),
        )
        set_object_tags(bucket_name, dto)
        return ApiResponse.on_success(SuccessStatus.STORAGE_OBJECT_TAGS_SET)
    return _handle(work)


@storage_bp.route('/buckets/<bucket_name>/objects/tags', methods=['DELETE'])
@jwt_required()
@storage_required('MANAGE')
def api_delete_tags(bucket_name: str):
    object_name = request.args.get('objectName', '')
    def work():
        if not object_name:
            return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "objectName 쿼리 파라미터가 필요합니다.")
        delete_object_tags(bucket_name, object_name)
        return ApiResponse.on_success(SuccessStatus.STORAGE_OBJECT_TAGS_DELETE)
    return _handle(work)
