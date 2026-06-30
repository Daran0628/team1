from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


# ──────────────────────────────────────────────
# /rbac/permission
# ──────────────────────────────────────────────

@dataclass
class PermissionResponseDTO:
    permission_id: str
    type:          str
    actions:       List[str]
    description:   Optional[str] = None
    resources:     List[dict] = field(default_factory=list)
    # resources 항목: {"resourceType": "BUCKET"|"OBJECT", "resourceId": "<uuid>", "resourceName": "<name>"}


# ──────────────────────────────────────────────
# /rbac/role
# ──────────────────────────────────────────────

@dataclass
class RoleResponseDTO:
    role_id:     str
    role_name:   str
    description: Optional[str]
    permissions: list[PermissionResponseDTO] = field(default_factory=list)


# ──────────────────────────────────────────────
# /rbac/rolebinding
# ──────────────────────────────────────────────

@dataclass
class RoleBindingResponseDTO:
    subject_type: str
    subject_id:   str
    role_id:      str
    role_name:    str
    granted_by:   str
    granted_at:   datetime


# ──────────────────────────────────────────────
# /rbac/group  (DEPARTMENT / TEAM 바인딩 목록용)
# ──────────────────────────────────────────────

@dataclass
class GroupBindingResponseDTO:
    subject_type: str          # DEPARTMENT or TEAM
    subject_id:   str
    role_id:      str
    role_name:    str
    granted_by:   str
    granted_at:   datetime
