from domain.model.Group import Group
from domain.model.Member import Member
from domain.model.Permission import Permission
from domain.model.Role import Role
from domain.model.RoleBinding import RoleBinding
from web.dto.GroupResponseDTO import GroupMemberDTO, GroupResponseDTO
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
            type=permission.perm_type,
            action=permission.action,
            resource_ids=permission.resource_ids,
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
            role_id=binding.role_id,
            role_name=binding.role.role_name,
            granted_by=binding.granted_by,
            granted_at=binding.granted_at,
        )

    @staticmethod
    def to_group_member_dto(member: Member) -> GroupMemberDTO:
        return GroupMemberDTO(
            member_id=member.id,
            account_id=member.account_id,
            name_ko=member.name_ko,
            department_id=member.department_id,
        )

    @staticmethod
    def to_group_dto(group: Group) -> GroupResponseDTO:
        return GroupResponseDTO(
            group_id=group.id,
            group_name=group.group_name,
            description=group.description,
            members=[RBACConverter.to_group_member_dto(m) for m in group.members],
        )
