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
                if 'MANAGE' in perm.action_list:
                    return 'MANAGE'
                if 'READ' in perm.action_list:
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
    OBJECT 권한 + 버킷 레벨 접근 → True (그 버킷에 접근 가능한 오브젝트가 하나라도 있으면)
    """
    if not perm._resources:
        return True   # 리소스 제한 없음 → 전체 허용

    bucket_ids = perm.bucket_ids
    object_ids = perm.object_ids

    # ── BUCKET 레벨 권한 확인 ─────────────────────────────────
    if bucket_ids and bucket_name:
        from domain.model.StorageBucket import StorageBucket
        bucket = StorageBucket.query.filter_by(bucket_name=bucket_name).first()
        if bucket and bucket.bucket_id in bucket_ids:
            return True

    # ── OBJECT 레벨 권한 확인 — 특정 오브젝트 접근 ───────────────
    if object_ids and object_name and bucket_name:
        from domain.model.StorageResource import StorageResource
        resource = StorageResource.query.filter_by(
            bucket_name=bucket_name,
            s3_key=object_name,
            is_deleted=False,
        ).first()
        if resource and resource.resource_id in object_ids:
            return True

    # ── OBJECT 권한 → 버킷 레벨(목록) 접근 허용 ─────────────────
    # object_name 없이 bucket_name만 있는 요청(예: 오브젝트 목록 조회):
    # 해당 버킷에 접근 가능한 오브젝트가 하나라도 있으면 버킷 접근 허용
    if object_ids and bucket_name and not object_name:
        from domain.model.StorageResource import StorageResource
        accessible = StorageResource.query.filter(
            StorageResource.bucket_name == bucket_name,
            StorageResource.resource_id.in_(object_ids),
            StorageResource.is_deleted == False,
        ).first()
        if accessible:
            return True

    return False


def check_storage_action(required_action: str) -> bool:
    """
    required_action: StorageAction 값 (READ / DOWNLOAD / UPLOAD / DELETE / MANAGE / SHARE)
    Flask request context에서 bucket_name, objectName을 자동으로 읽어 리소스 범위 검사.
    """
    from flask import request

    if get_jwt().get('role', '') in _ADMIN_ACCOUNT_TYPES:
        return True

    member = _get_member()
    if not member:
        return False

    bucket_name = (request.view_args or {}).get('bucket_name')
    _body = request.get_json(silent=True) or {}
    object_name = (
        request.args.get('objectName')
        or _body.get('objectName')
        or _body.get('sourceObject')
    )

    for binding in _collect_all_bindings(member):
        role = binding.role
        if role.role_name in _ADMIN_ROLE_NAMES:
            return True
        for perm in role.permissions:
            if perm.perm_type != 'STORAGE':
                continue
            if required_action not in perm.action_list and 'MANAGE' not in perm.action_list:
                continue

            # 버킷/오브젝트 지정 없는 메타 요청 (전체 버킷 목록, 리소스 목록 등)
            # → 해당 액션 권한이 존재하기만 하면 허용 (리소스 범위는 개별 요청에서 검사)
            if bucket_name is None and object_name is None:
                return True

            if _storage_resource_allowed(perm, bucket_name, object_name):
                return True

    return False


def get_accessible_object_keys(bucket_name: str) -> list[str] | None:
    """
    현재 로그인 유저가 해당 버킷에서 접근 가능한 오브젝트의 s3_key 목록 반환.
    None  → 버킷 전체 허용 (BUCKET 레벨 권한 또는 전체 권한 보유)
    list  → 접근 가능한 s3_key 목록 (OBJECT 레벨 권한만 보유)
    """
    if get_jwt().get('role', '') in _ADMIN_ACCOUNT_TYPES:
        return None

    member = _get_member()
    if not member:
        return []

    accessible_object_ids: set[str] = set()

    for binding in _collect_all_bindings(member):
        role = binding.role
        if role.role_name in _ADMIN_ROLE_NAMES:
            return None
        for perm in role.permissions:
            if perm.perm_type != 'STORAGE':
                continue
            if not any(a in perm.action_list for a in ('MANAGE', 'READ')):
                continue

            # 전체 허용 (리소스 제한 없음)
            if not perm._resources:
                return None

            # BUCKET 레벨 권한 → 해당 버킷 전체 허용
            if perm.bucket_ids:
                from domain.model.StorageBucket import StorageBucket
                bucket = StorageBucket.query.filter_by(bucket_name=bucket_name).first()
                if bucket and bucket.bucket_id in perm.bucket_ids:
                    return None

            # OBJECT 레벨 권한 → 오브젝트 ID 수집
            if perm.object_ids:
                accessible_object_ids.update(perm.object_ids)

    if not accessible_object_ids:
        return []

    from domain.model.StorageResource import StorageResource
    resources = StorageResource.query.filter(
        StorageResource.bucket_name == bucket_name,
        StorageResource.resource_id.in_(accessible_object_ids),
        StorageResource.is_deleted == False,
    ).all()
    return [r.s3_key for r in resources]


def get_accessible_bucket_names() -> set[str] | None:
    """
    현재 로그인 유저가 접근 가능한 버킷 이름 집합 반환.
    None  → 전체 허용 (admin 또는 리소스 제한 없는 READ/MANAGE 권한)
    set   → 접근 가능한 bucket_name 집합 (빈 set = 접근 가능 버킷 없음)
    """
    if get_jwt().get('role', '') in _ADMIN_ACCOUNT_TYPES:
        return None

    member = _get_member()
    if not member:
        return set()

    accessible: set[str] = set()

    for binding in _collect_all_bindings(member):
        role = binding.role
        if role.role_name in _ADMIN_ROLE_NAMES:
            return None
        for perm in role.permissions:
            if perm.perm_type != 'STORAGE':
                continue
            if not any(a in perm.action_list for a in ('READ', 'MANAGE')):
                continue

            # 리소스 제한 없음 → 전체 허용
            if not perm._resources:
                return None

            # BUCKET 레벨 권한 → 해당 버킷 이름 추가
            if perm.bucket_ids:
                from domain.model.StorageBucket import StorageBucket
                for b in StorageBucket.query.filter(
                    StorageBucket.bucket_id.in_(perm.bucket_ids)
                ).all():
                    accessible.add(b.bucket_name)

            # OBJECT 레벨 권한 → 해당 오브젝트가 속한 버킷 이름 추가
            if perm.object_ids:
                from domain.model.StorageResource import StorageResource
                for r in StorageResource.query.filter(
                    StorageResource.resource_id.in_(perm.object_ids),
                    StorageResource.is_deleted == False,
                ).all():
                    accessible.add(r.bucket_name)

    return accessible


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


# ── VDI 접근 권한 확인 ────────────────────────────────────────

# 자신의 VDI에 대해 권한 없이 허용하는 기본 액션
_VDI_SELF_ALLOWED = {'CONNECT', 'POWER_ON', 'POWER_OFF', 'REBOOT', 'SNAPSHOT'}


def check_vdi_action(required_action: str, vdi_assigned_to: str | None = None) -> bool:
    """
    required_action: VdiAction 값 (CONNECT / POWER_ON / POWER_OFF / REBOOT / SNAPSHOT / MANAGE 등)
    vdi_assigned_to: VDI에 할당된 member_id — 현재 유저와 같으면 기본 액션 자동 허용.
    """
    if get_jwt().get('role', '') in _ADMIN_ACCOUNT_TYPES:
        return True

    member = _get_member()
    if not member:
        return False

    # 자신의 VDI에 대한 기본 작업은 Role 없이 허용
    if vdi_assigned_to and str(member.id) == str(vdi_assigned_to):
        if required_action in _VDI_SELF_ALLOWED:
            return True

    for binding in _collect_all_bindings(member):
        role = binding.role
        if role.role_name in _ADMIN_ROLE_NAMES:
            return True
        for perm in role.permissions:
            if perm.perm_type != 'VDI':
                continue
            if required_action in perm.action_list or 'MANAGE' in perm.action_list:
                return True

    return False


def vdi_required(action: str):
    """
    action: VdiAction 값
    vdi_assigned_to는 view_args에서 vdi_id를 통해 DB 조회로 확인.
    @jwt_required() 아래에 붙여서 사용.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from flask import request
            from domain.model.Vdi import Vdi

            vdi_id = (request.view_args or {}).get('vdi_id')
            assigned_to = None
            if vdi_id:
                vdi = Vdi.query.get(vdi_id)
                assigned_to = vdi.assigned_to if vdi else None

            if not check_vdi_action(action, assigned_to):
                return ApiResponse.on_failure(ErrorStatus._FORBIDDEN)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
