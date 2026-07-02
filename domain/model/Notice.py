import uuid
import sqlalchemy as sa

from domain.model.BaseEntity import BaseEntity
from extensions import db


class Notice(BaseEntity):
    __tablename__ = "tb_notice"

    id = db.Column(
        "notice_id",
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    member_id = db.Column(
        db.String(36),
        db.ForeignKey("tb_members.member_id"),
        nullable=False
    )

    title     = db.Column(db.String(100), nullable=False)
    content   = db.Column(db.Text,        nullable=False)
    view_count = db.Column(db.Integer,   nullable=False, default=0)
    is_pinned  = db.Column(db.Boolean,   nullable=False, default=False)

    author = db.relationship("Member", backref="notices", lazy=True)

    def __repr__(self):
        return f"<Notice id={self.id} title={self.title}>"