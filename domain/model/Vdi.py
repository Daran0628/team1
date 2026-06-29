import uuid
from datetime import datetime, timezone

import sqlalchemy as sa

from extensions import db


class Vdi(db.Model):
    __tablename__ = "tb_vdi"

    vdi_id         = db.Column(db.String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    container_name = db.Column(db.String(100), nullable=False, unique=True)
    image          = db.Column(db.String(200), nullable=False)

    status = db.Column(
        sa.Enum('RUNNING', 'STOPPED', 'EXITED', name='vdi_status'),
        nullable=False,
        default='STOPPED',
    )

    assigned_to = db.Column(db.String(36), nullable=False, unique=True)  # member_id

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    snapshots = db.relationship('VdiSnapshot', back_populates='vdi',
                                cascade='all, delete-orphan', lazy='select')

    def __repr__(self) -> str:
        return f"<Vdi id={self.vdi_id} name={self.container_name} status={self.status}>"


class VdiSnapshot(db.Model):
    __tablename__ = "tb_vdi_snapshot"

    snapshot_id   = db.Column(db.String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    vdi_id        = db.Column(db.String(36),  db.ForeignKey('tb_vdi.vdi_id', ondelete='CASCADE'), nullable=False)
    snapshot_name = db.Column(db.String(100), nullable=False)
    image_tag     = db.Column(db.String(200), nullable=False)
    created_by    = db.Column(db.String(36),  nullable=False)  # member_id

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    vdi = db.relationship('Vdi', back_populates='snapshots')

    def __repr__(self) -> str:
        return f"<VdiSnapshot id={self.snapshot_id} vdi={self.vdi_id} tag={self.image_tag}>"
