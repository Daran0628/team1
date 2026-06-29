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

    @jwt_required() 아래에 붙여야 JWT 컨텍스트가 준비된 상태에서 실행됨.
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

def check_storage_action(required_action: str) -> bool:
    """
    required_action: StorageAction 값 (READ / DOWNLOAD / UPLOAD / DELETE / MOVE / MANAGE)
    MANAGE 권한은 모든 action을 허용.
    """
    if get_jwt().get('role', '') in _ADMIN_ACCOUNT_TYPES:
        return True

    member = _get_member()
    if not member:
        return False

    for binding in _collect_all_bindings(member):
        role = binding.role
        if role.role_name in _ADMIN_ROLE_NAMES:
            return True
        for perm in role.permissions:
            if perm.perm_type == 'STORAGE':
                if perm.action in ('MANAGE', required_action):
                    return True
    return False


def storage_required(action: str):
    """
    action: StorageAction 값 (READ / DOWNLOAD / UPLOAD / DELETE / MOVE / MANAGE)
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
