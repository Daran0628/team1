import uuid
from datetime import datetime, timezone

from extensions import db


class StorageResource(db.Model):
    __tablename__ = "tb_storage_resource"

    resource_id   = db.Column(db.String(36),   primary_key=True, default=lambda: str(uuid.uuid4()))
    bucket_name   = db.Column(db.String(63),   db.ForeignKey('tb_storage_bucket.bucket_name', ondelete='CASCADE'), nullable=False)
    resource_name = db.Column(db.String(255),  nullable=False)
    s3_key        = db.Column(db.String(1000), nullable=False)
    owner_id      = db.Column(db.String(36),   nullable=False)
    is_deleted    = db.Column(db.Boolean,      nullable=False, default=False)
    created_at    = db.Column(db.DateTime,     nullable=False, default=lambda: datetime.now(timezone.utc))

    bucket = db.relationship(
        'StorageBucket',
        back_populates='resources',
        foreign_keys=[bucket_name],
    )

    def __repr__(self) -> str:
        return f"<StorageResource bucket={self.bucket_name} key={self.s3_key}>"
