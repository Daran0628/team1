from functools import wraps

from flask_jwt_extended import get_jwt, get_jwt_identity

from core.response.ApiResponse import ApiResponse
from core.response.ErrorStatus import ErrorStatus

# JWT role 클레임(account_type)이 이 중 하나면 RBAC 전체 허용
_ADMIN_ACCOUNT_TYPES = {'ADMIN', 'SUPERADMIN'}
# tb_role.role_name이 이 중 하나면 RBAC 전체 허용
_ADMIN_ROLE_NAMES    = {'ADMIN', 'USER-ADMIN'}


def check_rbac_level() -> str | None:
    """
    현재 요청 사용자의 RBAC 접근 수준을 반환.
    'MANAGE' : 전체 허용
    'READ'   : 조회만 허용
    None     : 접근 불가
    """
    from domain.enum.SubjectType import SubjectType
    from domain.model.Member import Member
    from domain.model.RoleBinding import RoleBinding

    # 1. account_type 기반 즉시 허용
    claims = get_jwt()
    if claims.get('role', '') in _ADMIN_ACCOUNT_TYPES:
        return 'MANAGE'

    # 2. 멤버 조회
    identity = get_jwt_identity()          # account_id
    member = Member.query.filter_by(account_id=identity).first()
    if not member:
        return None

    # 3. 직접 바인딩 + 그룹 바인딩 수집
    direct_bindings = RoleBinding.query.filter_by(
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

    # 4. 권한 평가 (MANAGE 발견 즉시 반환, READ 메모 후 계속)
    best = None
    for binding in direct_bindings + group_bindings:
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
