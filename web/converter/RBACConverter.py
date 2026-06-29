from domain.model.Permission import Permission
from domain.model.Role import Role
from domain.model.RoleBinding import RoleBinding
from web.dto.RBACResponseDTO import (
    GroupBindingResponseDTO,
    PermissionResponseDTO,
    RoleBindingResponseDTO,
    RoleResponseDTO,
)


class RBACConverter:

    @staticmethod
    def to_permission_dto(permission: Permission) -> PermissionResponseDTO:
        return PermissionResponseDTO(
            permission_id=permission.permission_id,
            resource=permission.resource,
            action=permission.action,
        )

    @staticmethod
    def to_role_dto(role: Role) -> RoleResponseDTO:
        return RoleResponseDTO(
            role_id=role.role_id,
            role_name=role.role_name,
            description=role.description,
            permissions=[RBACConverter.to_permission_dto(p) for p in role.permissions],
        )

    @staticmethod
    def to_binding_dto(binding: RoleBinding) -> RoleBindingResponseDTO:
        return RoleBindingResponseDTO(
            subject_type=binding.subject_type.value,
            subject_id=binding.subject_id,
            resource_type=binding.resource_type,
            resource_id=binding.resource_id,
            role_id=binding.role_id,
            role_name=binding.role.role_name,
            granted_by=binding.granted_by,
            granted_at=binding.granted_at,
        )

    @staticmethod
    def to_group_binding_dto(binding: RoleBinding) -> GroupBindingResponseDTO:
        return GroupBindingResponseDTO(
            subject_type=binding.subject_type.value,
            subject_id=binding.subject_id,
            resource_type=binding.resource_type,
            resource_id=binding.resource_id,
            role_id=binding.role_id,
            role_name=binding.role.role_name,
            granted_by=binding.granted_by,
            granted_at=binding.granted_at,
        )
