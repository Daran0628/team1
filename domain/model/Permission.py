import uuid

from extensions import db
from domain.model.RolePermission import role_permission_table


class Permission(db.Model):
    __tablename__ = "tb_permission"

    permission_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    resource      = db.Column(db.String(30), nullable=False)
    action        = db.Column(db.String(30), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("resource", "action", name="uk_permission"),
    )

    roles = db.relationship("Role", secondary=role_permission_table, back_populates="permissions")

    def __repr__(self) -> str:
        return f"<Permission {self.resource}:{self.action}>"
