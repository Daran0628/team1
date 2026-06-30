from dataclasses import dataclass, field
from typing import Optional, List

from domain.enum.SubjectType import SubjectType


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
    type:        str
    actions:     List[str]
    resources:   List[dict] = field(default_factory=list)
    description: Optional[str] = None
    # resources 항목 형식: {"resourceType": "BUCKET"|"OBJECT", "resourceId": "<uuid>"}

    _VALID_RESOURCE_TYPES = {'BUCKET', 'OBJECT'}

    def __post_init__(self):
        from domain.enum.StorageAction import StorageAction
        from domain.enum.VdiAction import VdiAction
        from domain.enum.RbacAction import RbacAction

        _valid_actions: dict = {
            'STORAGE': {a.value for a in StorageAction},
            'VDI':     {a.value for a in VdiAction},
            'RBAC':    {a.value for a in RbacAction},
        }
        if self.type not in _valid_actions:
            raise ValueError(f"type은 {list(_valid_actions.keys())} 중 하나여야 합니다.")
        if not isinstance(self.actions, list) or len(self.actions) == 0:
            raise ValueError("actions는 비어있지 않은 배열이어야 합니다.")
        invalid = [a for a in self.actions if a not in _valid_actions[self.type]]
        if invalid:
            raise ValueError(f"유효하지 않은 action: {invalid}. 허용: {sorted(_valid_actions[self.type])}")
        if not isinstance(self.resources, list):
            raise ValueError("resources는 배열이어야 합니다.")
        for r in self.resources:
            if not isinstance(r, dict):
                raise ValueError("resources의 각 항목은 {resourceType, resourceId} 객체여야 합니다.")
            rt = r.get('resourceType', '')
            rid = r.get('resourceId', '')
            if rt not in self._VALID_RESOURCE_TYPES:
                raise ValueError(f"resourceType은 {self._VALID_RESOURCE_TYPES} 중 하나여야 합니다.")
            if not rid or not rid.strip():
                raise ValueError("resourceId는 비어있지 않은 문자열이어야 합니다.")


@dataclass
class AssignPermissionRequestDTO:
    role_id:        str
    permission_ids: list    # 단건 또는 복수 ["id1", "id2", ...]

    def __post_init__(self):
        if not self.role_id or not self.role_id.strip():
            raise ValueError("role_id는 필수입니다.")
        if not isinstance(self.permission_ids, list) or len(self.permission_ids) == 0:
            raise ValueError("permissionIds는 비어있지 않은 배열이어야 합니다.")
        if any(not isinstance(p, str) or not p.strip() for p in self.permission_ids):
            raise ValueError("permissionIds의 각 항목은 비어있지 않은 문자열이어야 합니다.")


# ──────────────────────────────────────────────
# /rbac/rolebinding  (MEMBER / DEPARTMENT / TEAM)
# ──────────────────────────────────────────────

@dataclass
class CreateRoleBindingRequestDTO:
    subject_type: str
    subject_id:   str
    role_id:      str

    def __post_init__(self):
        valid_subjects = {s.value for s in SubjectType}
        if self.subject_type not in valid_subjects:
            raise ValueError(f"subject_type은 {valid_subjects} 중 하나여야 합니다.")
        if not self.subject_id or not self.subject_id.strip():
            raise ValueError("subject_id는 필수입니다.")
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
    subject_type: str          # DEPARTMENT or TEAM only
    subject_id:   str
    role_id:      str

    _GROUP_TYPES = {SubjectType.DEPARTMENT.value, SubjectType.TEAM.value}

    def __post_init__(self):
        if self.subject_type not in self._GROUP_TYPES:
            raise ValueError(f"subject_type은 {self._GROUP_TYPES} 중 하나여야 합니다.")
        if not self.subject_id or not self.subject_id.strip():
            raise ValueError("subject_id는 필수입니다.")
        if not self.role_id or not self.role_id.strip():
            raise ValueError("role_id는 필수입니다.")
