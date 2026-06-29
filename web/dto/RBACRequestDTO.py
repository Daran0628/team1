from dataclasses import dataclass
from typing import Optional

from domain.enum.SubjectType import SubjectType
from domain.enum.ResourceType import ResourceType


# ──────────────────────────────────────────────
# /rbac/role
# ──────────────────────────────────────────────

@dataclass
class CreateRoleRequestDTO:
    role_name:   str
    description: Optional[str] = None

    def __post_init__(self):
        if not self.role_name or not self.role_name.strip():
            raise ValueError("role_name은 필수입니다.")


@dataclass
class UpdateRoleRequestDTO:
    role_name:   Optional[str] = None
    description: Optional[str] = None

    def __post_init__(self):
        if self.role_name is not None and not self.role_name.strip():
            raise ValueError("role_name은 빈 값일 수 없습니다.")


# ──────────────────────────────────────────────
# /rbac/permission
# ──────────────────────────────────────────────

@dataclass
class CreatePermissionRequestDTO:
    resource: str
    action:   str

    def __post_init__(self):
        valid_resources = {r.value for r in ResourceType}
        if self.resource not in valid_resources:
            raise ValueError(f"resource는 {valid_resources} 중 하나여야 합니다.")
        if not self.action or not self.action.strip():
            raise ValueError("action은 필수입니다.")


@dataclass
class AssignPermissionRequestDTO:
    role_id:       str
    permission_id: str

    def __post_init__(self):
        if not self.role_id or not self.role_id.strip():
            raise ValueError("role_id는 필수입니다.")
        if not self.permission_id or not self.permission_id.strip():
            raise ValueError("permission_id는 필수입니다.")


# ──────────────────────────────────────────────
# /rbac/rolebinding  (MEMBER / DEPARTMENT / TEAM)
# ──────────────────────────────────────────────

@dataclass
class CreateRoleBindingRequestDTO:
    subject_type:  str
    subject_id:    str
    resource_type: str
    resource_id:   str
    role_id:       str

    def __post_init__(self):
        valid_subjects   = {s.value for s in SubjectType}
        valid_resources  = {r.value for r in ResourceType}

        if self.subject_type not in valid_subjects:
            raise ValueError(f"subject_type은 {valid_subjects} 중 하나여야 합니다.")
        if self.resource_type not in valid_resources:
            raise ValueError(f"resource_type은 {valid_resources} 중 하나여야 합니다.")
        if not self.subject_id or not self.subject_id.strip():
            raise ValueError("subject_id는 필수입니다.")
        if not self.resource_id or not self.resource_id.strip():
            raise ValueError("resource_id는 필수입니다.")
        if not self.role_id or not self.role_id.strip():
            raise ValueError("role_id는 필수입니다.")


@dataclass
class UpdateRoleBindingRequestDTO:
    role_id: str

    def __post_init__(self):
        if not self.role_id or not self.role_id.strip():
            raise ValueError("role_id는 필수입니다.")


# ──────────────────────────────────────────────
# /rbac/group  (DEPARTMENT / TEAM 전용)
# ──────────────────────────────────────────────

@dataclass
class CreateGroupBindingRequestDTO:
    subject_type:  str          # DEPARTMENT or TEAM only
    subject_id:    str
    resource_type: str
    resource_id:   str
    role_id:       str

    _GROUP_TYPES = {SubjectType.DEPARTMENT.value, SubjectType.TEAM.value}

    def __post_init__(self):
        if self.subject_type not in self._GROUP_TYPES:
            raise ValueError(f"subject_type은 {self._GROUP_TYPES} 중 하나여야 합니다.")

        valid_resources = {r.value for r in ResourceType}
        if self.resource_type not in valid_resources:
            raise ValueError(f"resource_type은 {valid_resources} 중 하나여야 합니다.")
        if not self.subject_id or not self.subject_id.strip():
            raise ValueError("subject_id는 필수입니다.")
        if not self.resource_id or not self.resource_id.strip():
            raise ValueError("resource_id는 필수입니다.")
        if not self.role_id or not self.role_id.strip():
            raise ValueError("role_id는 필수입니다.")
