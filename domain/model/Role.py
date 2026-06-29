import uuid

from extensions import db
from domain.model.RolePermission import role_permission_table


class Role(db.Model):
    __tablename__ = "tb_role"

    role_id     = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    role_name   = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)

    permissions = db.relationship("Permission", secondary=role_permission_table, back_populates="roles")

    def __repr__(self) -> str:
        return f"<Role id={self.role_id} name={self.role_name}>"
