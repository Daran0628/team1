import uuid
from datetime import datetime, timezone

from extensions import db


class StorageBucket(db.Model):
    __tablename__ = "tb_storage_bucket"

    bucket_id   = db.Column(db.String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    bucket_name = db.Column(db.String(63),  nullable=False, unique=True)
    created_by  = db.Column(db.String(36),  nullable=False)  # member_id
    created_at  = db.Column(db.DateTime,    nullable=False, default=lambda: datetime.now(timezone.utc))

    resources = db.relationship(
        'StorageResource',
        back_populates='bucket',
        cascade='all, delete-orphan',
        lazy='dynamic',
        foreign_keys='StorageResource.bucket_name',
        primaryjoin='StorageBucket.bucket_name == StorageResource.bucket_name',
    )

    def __repr__(self) -> str:
        return f"<StorageBucket name={self.bucket_name}>"
