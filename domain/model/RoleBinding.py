import sqlalchemy as sa
from datetime import datetime, timezone

from extensions import db
from domain.enum.SubjectType import SubjectType


class RoleBinding(db.Model):
    __tablename__ = "tb_role_binding"

    subject_type  = db.Column(
        sa.Enum(SubjectType, values_callable=lambda e: [i.value for i in e]),
        primary_key=True,
    )
    subject_id    = db.Column(db.String(36), primary_key=True)

    role_id    = db.Column(db.String(36), db.ForeignKey("tb_role.role_id"), nullable=False)
    granted_by = db.Column(db.String(36), nullable=False)
    granted_at = db.Column(db.DateTime,  nullable=False, default=lambda: datetime.now(timezone.utc))

    role = db.relationship("Role")

    def __repr__(self) -> str:
        return (
            f"<RoleBinding {self.subject_type.value}:{self.subject_id}"
            f" role={self.role_id}>"
        )
