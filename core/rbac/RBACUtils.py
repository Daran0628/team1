from functools import wraps

from flask_jwt_extended import get_jwt, get_jwt_identity

from core.response.ApiResponse import ApiResponse
from core.response.ErrorStatus import ErrorStatus

_ADMIN_ACCOUNT_TYPES = {'ADMIN', 'SUPERADMIN'}
_ADMIN_ROLE_NAMES    = {'ADMIN', 'USER-ADMIN'}


# ── 공통 헬퍼 ────────────────────────────────────────────────

def _get_member():
    from domain.model.Member import Member
    return Member.query.filter_by(account_id=get_jwt_identity()).first()


def _collect_all_bindings(member):
    """멤버의 직접 바인딩 + 그룹 바인딩을 모두 반환."""
    from domain.enum.SubjectType import SubjectType
    from domain.model.RoleBinding import RoleBinding

    direct = RoleBinding.query.filter_by(
        subject_type=SubjectType.MEMBER,
        subject_id=member.id,
    ).all()

    group_ids = [g.id for g in member.groups]
    group_bindings = (
        RoleBinding.query.filter(
            RoleBinding.subject_type == SubjectType.TEAM,
            RoleBinding.subject_id.in_(group_ids),
        ).all()
        if group_ids else []
    )
    return direct + group_bindings


# ── RBAC 접근 레벨 확인 ──────────────────────────────────────

def check_rbac_level() -> str | None:
    """
    'MANAGE' : 전체 허용
    'READ'   : 조회만 허용
    None     : 접근 불가
    """
    if get_jwt().get('role', '') in _ADMIN_ACCOUNT_TYPES:
        return 'MANAGE'

    member = _get_member()
    if not member:
        return None

    best = None
    for binding in _collect_all_bindings(member):
        role = binding.role
        if role.role_name in _ADMIN_ROLE_NAMES:
            return 'MANAGE'
        for perm in role.permissions:
            if perm.perm_type == 'RBAC':
                if perm.action == 'MANAGE':
                    return 'MANAGE'
                if perm.action == 'READ':
                    best = 'READ'
    return best


def rbac_required(level: str):
    """
    level='READ'   → READ 또는 MANAGE 보유 시 허용
    level='MANAGE' → MANAGE 보유 시만 허용
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            actual = check_rbac_level()
            allowed = (actual == 'MANAGE') or (level == 'READ' and actual == 'READ')
            if not allowed:
                return ApiResponse.on_failure(ErrorStatus._FORBIDDEN)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ── Storage 접근 권한 확인 ───────────────────────────────────

def _storage_resource_allowed(perm, bucket_name: str | None, object_name: str | None) -> bool:
    """
    권한에 resource 제한이 없으면 → True (전체 허용)
    BUCKET resource 매칭 → True (해당 버킷 전체 허용)
    OBJECT resource 매칭 → True (해당 오브젝트만 허용)
    둘 다 해당 없음 → False
    """
    if not perm._resources:
        return True

    bucket_ids = perm.bucket_ids
    object_ids  = perm.object_ids

    if bucket_ids and bucket_name:
        from domain.model.StorageBucket import StorageBucket
        bucket = StorageBucket.query.filter_by(bucket_name=bucket_name).first()
        if bucket and bucket.bucket_id in bucket_ids:
            return True

    if object_ids and object_name and bucket_name:
        from domain.model.StorageResource import StorageResource
        resource = StorageResource.query.filter_by(
            bucket_name=bucket_name,
            s3_key=object_name,
            is_deleted=False,
        ).first()
        if resource and resource.resource_id in object_ids:
            return True

    return False


def check_storage_action(required_action: str) -> bool:
    """
    required_action: StorageAction 값 (READ / DOWNLOAD / UPLOAD / DELETE / MANAGE)
    Flask request context에서 bucket_name, objectName을 자동으로 읽어 리소스 범위 검사.
    """
    from flask import request

    if get_jwt().get('role', '') in _ADMIN_ACCOUNT_TYPES:
        return True

    member = _get_member()
    if not member:
        return False

    bucket_name = (request.view_args or {}).get('bucket_name')
    object_name = (
        request.args.get('objectName')
        or (request.get_json(silent=True) or {}).get('objectName')
        or (request.get_json(silent=True) or {}).get('sourceObject')
    )

    for binding in _collect_all_bindings(member):
        role = binding.role
        if role.role_name in _ADMIN_ROLE_NAMES:
            return True
        for perm in role.permissions:
            if perm.perm_type == 'STORAGE' and perm.action in ('MANAGE', required_action):
                if _storage_resource_allowed(perm, bucket_name, object_name):
                    return True
    return False


def storage_required(action: str):
    """
    action: StorageAction 값 (READ / DOWNLOAD / UPLOAD / DELETE / MANAGE)
    @jwt_required() 아래에 붙여서 사용.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not check_storage_action(action):
                return ApiResponse.on_failure(ErrorStatus._FORBIDDEN)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
