import uuid

from extensions import db
from domain.model.RolePermission import role_permission_table


class PermissionResource(db.Model):
    __tablename__ = "tb_permission_resource"

    permission_id = db.Column(
        db.String(36),
        db.ForeignKey('tb_permission.permission_id', ondelete='CASCADE'),
        primary_key=True,
    )
    resource_type = db.Column(db.String(10), nullable=False, primary_key=True)  # BUCKET | OBJECT
    resource_id   = db.Column(db.String(36), nullable=False, primary_key=True)


class Permission(db.Model):
    __tablename__ = "tb_permission"

    permission_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    perm_type     = db.Column('type',   db.String(30), nullable=False)
    action        = db.Column(db.String(30), nullable=False)

    _resources = db.relationship('PermissionResource', lazy='select', cascade='all, delete-orphan')
    roles = db.relationship("Role", secondary=role_permission_table, back_populates="permissions")

    @property
    def resource_ids(self) -> list[str]:
        return [r.resource_id for r in self._resources]

    @property
    def bucket_ids(self) -> list[str]:
        return [r.resource_id for r in self._resources if r.resource_type == 'BUCKET']

    @property
    def object_ids(self) -> list[str]:
        return [r.resource_id for r in self._resources if r.resource_type == 'OBJECT']

    def __repr__(self) -> str:
        return f"<Permission {self.perm_type}:{self.action}>"
