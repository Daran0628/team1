import logging
import uuid

from sqlalchemy.exc import IntegrityError

from domain.enum.SubjectType import SubjectType
from domain.model.Permission import Permission
from domain.model.Role import Role
from domain.model.RoleBinding import RoleBinding
from extensions import db
from web.converter.RBACConverter import RBACConverter
from web.dto.RBACRequestDTO import (
    AssignPermissionRequestDTO,
    CreatePermissionRequestDTO,
    CreateRoleBindingRequestDTO,
    CreateRoleRequestDTO,
    UpdateRoleBindingRequestDTO,
    UpdateRoleRequestDTO,
)
from web.dto.RBACResponseDTO import (
    GroupBindingResponseDTO,
    PermissionResponseDTO,
    RoleBindingResponseDTO,
    RoleResponseDTO,
)

logger = logging.getLogger(__name__)

_GROUP_TYPES = {SubjectType.DEPARTMENT, SubjectType.TEAM}


class RBACService:

    # ── Role ──────────────────────────────────────────────────

    def create_role(self, dto: CreateRoleRequestDTO) -> RoleResponseDTO:
        if Role.query.filter_by(role_name=dto.role_name).first():
            raise ValueError("ROLE_NAME_DUPLICATE")

        role = Role(
            role_id=str(uuid.uuid4()),
            role_name=dto.role_name,
            description=dto.description,
        )
        db.session.add(role)
        db.session.commit()
        return RBACConverter.to_role_dto(role)

    def get_all_roles(self) -> list[RoleResponseDTO]:
        return [RBACConverter.to_role_dto(r) for r in Role.query.all()]

    def get_role(self, role_id: str) -> RoleResponseDTO:
        role = Role.query.get(role_id)
        if not role:
            raise ValueError("ROLE_NOT_FOUND")
        return RBACConverter.to_role_dto(role)

    def update_role(self, role_id: str, dto: UpdateRoleRequestDTO) -> RoleResponseDTO:
        role = Role.query.get(role_id)
        if not role:
            raise ValueError("ROLE_NOT_FOUND")
        if dto.role_name:
            if Role.query.filter(Role.role_name == dto.role_name, Role.role_id != role_id).first():
                raise ValueError("ROLE_NAME_DUPLICATE")
            role.role_name = dto.role_name
        if dto.description is not None:
            role.description = dto.description
        db.session.commit()
        return RBACConverter.to_role_dto(role)

    def delete_role(self, role_id: str) -> None:
        role = Role.query.get(role_id)
        if not role:
            raise ValueError("ROLE_NOT_FOUND")
        try:
            db.session.delete(role)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError("ROLE_HAS_BINDINGS")

    # ── Permission ────────────────────────────────────────────

    def create_permission(self, dto: CreatePermissionRequestDTO) -> PermissionResponseDTO:
        if Permission.query.filter_by(resource=dto.resource, action=dto.action).first():
            raise ValueError("PERMISSION_DUPLICATE")

        perm = Permission(
            permission_id=str(uuid.uuid4()),
            resource=dto.resource,
            action=dto.action,
        )
        db.session.add(perm)
        db.session.commit()
        return RBACConverter.to_permission_dto(perm)

    def get_all_permissions(self, resource: str | None = None) -> list[PermissionResponseDTO]:
        q = Permission.query
        if resource:
            q = q.filter_by(resource=resource)
        return [RBACConverter.to_permission_dto(p) for p in q.all()]

    def delete_permission(self, permission_id: str) -> None:
        perm = Permission.query.get(permission_id)
        if not perm:
            raise ValueError("PERMISSION_NOT_FOUND")
        db.session.delete(perm)
        db.session.commit()

    def assign_permission(self, dto: AssignPermissionRequestDTO) -> None:
        role = Role.query.get(dto.role_id)
        if not role:
            raise ValueError("ROLE_NOT_FOUND")
        for perm_id in dto.permission_ids:
            perm = Permission.query.get(perm_id)
            if not perm:
                raise ValueError("PERMISSION_NOT_FOUND")
            if perm in role.permissions:
                raise ValueError("PERMISSION_ALREADY_ASSIGNED")
            role.permissions.append(perm)
        db.session.commit()

    def revoke_permission(self, role_id: str, permission_id: str) -> None:
        role = Role.query.get(role_id)
        if not role:
            raise ValueError("ROLE_NOT_FOUND")
        perm = Permission.query.get(permission_id)
        if not perm or perm not in role.permissions:
            raise ValueError("PERMISSION_NOT_FOUND")
        role.permissions.remove(perm)
        db.session.commit()

    # ── RoleBinding ───────────────────────────────────────────

    def create_binding(self, dto: CreateRoleBindingRequestDTO, granted_by: str) -> RoleBindingResponseDTO:
        subject_type = SubjectType(dto.subject_type)
        existing = RoleBinding.query.filter_by(
            subject_type=subject_type,
            subject_id=dto.subject_id,
            resource_type=dto.resource_type,
            resource_id=dto.resource_id,
        ).first()
        if existing:
            raise ValueError("BINDING_ALREADY_EXISTS")
        if not Role.query.get(dto.role_id):
            raise ValueError("ROLE_NOT_FOUND")

        binding = RoleBinding(
            subject_type=subject_type,
            subject_id=dto.subject_id,
            resource_type=dto.resource_type,
            resource_id=dto.resource_id,
            role_id=dto.role_id,
            granted_by=granted_by,
        )
        db.session.add(binding)
        db.session.commit()
        return RBACConverter.to_binding_dto(binding)

    def get_bindings(
        self,
        subject_types: list[str] | None = None,
        subject_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> list[RoleBindingResponseDTO]:
        q = RoleBinding.query
        if subject_types:
            q = q.filter(RoleBinding.subject_type.in_([SubjectType(s) for s in subject_types]))
        if subject_id:
            q = q.filter_by(subject_id=subject_id)
        if resource_type:
            q = q.filter_by(resource_type=resource_type)
        if resource_id:
            q = q.filter_by(resource_id=resource_id)
        return [RBACConverter.to_binding_dto(b) for b in q.all()]

    def update_binding(
        self,
        subject_type: str,
        subject_id: str,
        resource_type: str,
        resource_id: str,
        dto: UpdateRoleBindingRequestDTO,
    ) -> RoleBindingResponseDTO:
        binding = RoleBinding.query.filter_by(
            subject_type=SubjectType(subject_type),
            subject_id=subject_id,
            resource_type=resource_type,
            resource_id=resource_id,
        ).first()
        if not binding:
            raise ValueError("BINDING_NOT_FOUND")
        if not Role.query.get(dto.role_id):
            raise ValueError("ROLE_NOT_FOUND")
        binding.role_id = dto.role_id
        db.session.commit()
        return RBACConverter.to_binding_dto(binding)

    def delete_binding(
        self,
        subject_type: str,
        subject_id: str,
        resource_type: str,
        resource_id: str,
    ) -> None:
        binding = RoleBinding.query.filter_by(
            subject_type=SubjectType(subject_type),
            subject_id=subject_id,
            resource_type=resource_type,
            resource_id=resource_id,
        ).first()
        if not binding:
            raise ValueError("BINDING_NOT_FOUND")
        db.session.delete(binding)
        db.session.commit()

    # ── Group (DEPARTMENT / TEAM 전용) ────────────────────────

    def get_group_bindings(
        self,
        subject_type: str | None = None,
        subject_id: str | None = None,
        resource_type: str | None = None,
    ) -> list[GroupBindingResponseDTO]:
        filter_types = (
            [SubjectType(subject_type)] if subject_type
            else list(_GROUP_TYPES)
        )
        q = RoleBinding.query.filter(RoleBinding.subject_type.in_(filter_types))
        if subject_id:
            q = q.filter_by(subject_id=subject_id)
        if resource_type:
            q = q.filter_by(resource_type=resource_type)
        return [RBACConverter.to_group_binding_dto(b) for b in q.all()]
