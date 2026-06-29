import logging

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from core.response.ApiResponse import ApiResponse
from core.response.ErrorStatus import ErrorStatus
from core.response.SuccessStatus import SuccessStatus
from service.RBACService.RBACService import RBACService
from web.dto.RBACRequestDTO import (
    AssignPermissionRequestDTO,
    CreateGroupBindingRequestDTO,
    CreatePermissionRequestDTO,
    CreateRoleBindingRequestDTO,
    CreateRoleRequestDTO,
    UpdateRoleBindingRequestDTO,
    UpdateRoleRequestDTO,
)

logger = logging.getLogger(__name__)

rbac_bp = Blueprint("rbac", __name__, url_prefix="/api/rbac")
_service = RBACService()

_ERR_MAP = {
    "ROLE_NOT_FOUND":              ErrorStatus.RBAC_ROLE_NOT_FOUND,
    "ROLE_NAME_DUPLICATE":         ErrorStatus.RBAC_ROLE_NAME_DUPLICATE,
    "ROLE_HAS_BINDINGS":           ErrorStatus.RBAC_ROLE_HAS_BINDINGS,
    "PERMISSION_NOT_FOUND":        ErrorStatus.RBAC_PERMISSION_NOT_FOUND,
    "PERMISSION_DUPLICATE":        ErrorStatus.RBAC_PERMISSION_DUPLICATE,
    "PERMISSION_ALREADY_ASSIGNED": ErrorStatus.RBAC_PERMISSION_ALREADY_ASSIGNED,
    "BINDING_NOT_FOUND":           ErrorStatus.RBAC_BINDING_NOT_FOUND,
    "BINDING_ALREADY_EXISTS":      ErrorStatus.RBAC_BINDING_ALREADY_EXISTS,
}


def _handle(exc: Exception):
    msg = str(exc)
    return ApiResponse.on_failure(_ERR_MAP.get(msg, ErrorStatus._INTERNAL_SERVER_ERROR))


# ──────────────────────────────────────────────
# /api/rbac/role
# ──────────────────────────────────────────────

@rbac_bp.route("/role", methods=["POST"])
@jwt_required()
def create_role():
    data = request.get_json(silent=True) or {}
    try:
        dto = CreateRoleRequestDTO(
            role_name=data.get("roleName", ""),
            description=data.get("description"),
        )
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, str(e))

    try:
        result = _service.create_role(dto)
        return ApiResponse.on_success(SuccessStatus.RBAC_ROLE_CREATE, result)
    except ValueError as e:
        return _handle(e)


@rbac_bp.route("/role", methods=["GET"])
@jwt_required()
def get_all_roles():
    return ApiResponse.on_success(SuccessStatus.RBAC_ROLE_READ, _service.get_all_roles())


@rbac_bp.route("/role/<role_id>", methods=["GET"])
@jwt_required()
def get_role(role_id: str):
    try:
        return ApiResponse.on_success(SuccessStatus.RBAC_ROLE_READ, _service.get_role(role_id))
    except ValueError as e:
        return _handle(e)


@rbac_bp.route("/role/<role_id>", methods=["PUT"])
@jwt_required()
def update_role(role_id: str):
    data = request.get_json(silent=True) or {}
    try:
        dto = UpdateRoleRequestDTO(
            role_name=data.get("roleName"),
            description=data.get("description"),
        )
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, str(e))

    try:
        result = _service.update_role(role_id, dto)
        return ApiResponse.on_success(SuccessStatus.RBAC_ROLE_UPDATE, result)
    except ValueError as e:
        return _handle(e)


@rbac_bp.route("/role/<role_id>", methods=["DELETE"])
@jwt_required()
def delete_role(role_id: str):
    try:
        _service.delete_role(role_id)
        return ApiResponse.on_success(SuccessStatus.RBAC_ROLE_DELETE)
    except ValueError as e:
        return _handle(e)


# ──────────────────────────────────────────────
# /api/rbac/permission
# ──────────────────────────────────────────────

@rbac_bp.route("/permission", methods=["POST"])
@jwt_required()
def create_permission():
    data = request.get_json(silent=True) or {}
    try:
        dto = CreatePermissionRequestDTO(
            type=data.get("type", ""),
            actions=data.get("actions") or [],
            resource_ids=data.get("resourceIds") or [],
        )
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, str(e))

    try:
        result = _service.create_permission(dto)
        return ApiResponse.on_success(SuccessStatus.RBAC_PERMISSION_CREATE, result)
    except ValueError as e:
        return _handle(e)


@rbac_bp.route("/permission", methods=["GET"])
@jwt_required()
def get_all_permissions():
    type_ = request.args.get("type")
    return ApiResponse.on_success(
        SuccessStatus.RBAC_PERMISSION_READ,
        _service.get_all_permissions(type_),
    )


@rbac_bp.route("/permission/<permission_id>", methods=["DELETE"])
@jwt_required()
def delete_permission(permission_id: str):
    try:
        _service.delete_permission(permission_id)
        return ApiResponse.on_success(SuccessStatus.RBAC_PERMISSION_DELETE)
    except ValueError as e:
        return _handle(e)


@rbac_bp.route("/permission/assign", methods=["POST"])
@jwt_required()
def assign_permission():
    data = request.get_json(silent=True) or {}
    try:
        dto = AssignPermissionRequestDTO(
            role_id=data.get("roleId", ""),
            permission_ids=data.get("permissionIds", []),
        )
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, str(e))

    try:
        _service.assign_permission(dto)
        return ApiResponse.on_success(SuccessStatus.RBAC_PERMISSION_ASSIGN)
    except ValueError as e:
        return _handle(e)


@rbac_bp.route("/permission/assign", methods=["DELETE"])
@jwt_required()
def revoke_permission():
    role_id       = request.args.get("roleId", "")
    permission_id = request.args.get("permissionId", "")
    if not role_id or not permission_id:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "roleId, permissionId는 필수입니다.")

    try:
        _service.revoke_permission(role_id, permission_id)
        return ApiResponse.on_success(SuccessStatus.RBAC_PERMISSION_REVOKE)
    except ValueError as e:
        return _handle(e)


# ──────────────────────────────────────────────
# /api/rbac/rolebinding
# ──────────────────────────────────────────────

@rbac_bp.route("/rolebinding", methods=["POST"])
@jwt_required()
def create_binding():
    data       = request.get_json(silent=True) or {}
    granted_by = get_jwt_identity()
    try:
        dto = CreateRoleBindingRequestDTO(
            subject_type=data.get("subjectType", ""),
            subject_id=data.get("subjectId", ""),
            role_id=data.get("roleId", ""),
        )
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, str(e))

    try:
        result = _service.create_binding(dto, granted_by)
        return ApiResponse.on_success(SuccessStatus.RBAC_BINDING_CREATE, result)
    except ValueError as e:
        return _handle(e)


@rbac_bp.route("/rolebinding", methods=["GET"])
@jwt_required()
def get_bindings():
    subject_types = request.args.getlist("subjectType") or None
    result = _service.get_bindings(
        subject_types=subject_types,
        subject_id=request.args.get("subjectId"),
    )
    return ApiResponse.on_success(SuccessStatus.RBAC_BINDING_READ, result)


@rbac_bp.route("/rolebinding", methods=["PUT"])
@jwt_required()
def update_binding():
    data         = request.get_json(silent=True) or {}
    subject_type = request.args.get("subjectType", "")
    subject_id   = request.args.get("subjectId", "")

    if not all([subject_type, subject_id]):
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "쿼리 파라미터(subjectType, subjectId)가 필요합니다.")

    try:
        dto = UpdateRoleBindingRequestDTO(role_id=data.get("roleId", ""))
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, str(e))

    try:
        result = _service.update_binding(subject_type, subject_id, dto)
        return ApiResponse.on_success(SuccessStatus.RBAC_BINDING_UPDATE, result)
    except ValueError as e:
        return _handle(e)


@rbac_bp.route("/rolebinding", methods=["DELETE"])
@jwt_required()
def delete_binding():
    subject_type = request.args.get("subjectType", "")
    subject_id   = request.args.get("subjectId", "")

    if not all([subject_type, subject_id]):
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "쿼리 파라미터(subjectType, subjectId)가 필요합니다.")

    try:
        _service.delete_binding(subject_type, subject_id)
        return ApiResponse.on_success(SuccessStatus.RBAC_BINDING_DELETE)
    except ValueError as e:
        return _handle(e)


# ──────────────────────────────────────────────
# /api/rbac/group  (DEPARTMENT / TEAM 전용)
# ──────────────────────────────────────────────

@rbac_bp.route("/group", methods=["POST"])
@jwt_required()
def create_group_binding():
    data       = request.get_json(silent=True) or {}
    granted_by = get_jwt_identity()
    try:
        dto = CreateGroupBindingRequestDTO(
            subject_type=data.get("subjectType", ""),
            subject_id=data.get("subjectId", ""),
            role_id=data.get("roleId", ""),
        )
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, str(e))

    try:
        from web.dto.RBACRequestDTO import CreateRoleBindingRequestDTO as BindingDTO
        binding_dto = BindingDTO(
            subject_type=dto.subject_type,
            subject_id=dto.subject_id,
            role_id=dto.role_id,
        )
        result = _service.create_binding(binding_dto, granted_by)
        return ApiResponse.on_success(SuccessStatus.RBAC_BINDING_CREATE, result)
    except ValueError as e:
        return _handle(e)


@rbac_bp.route("/group", methods=["GET"])
@jwt_required()
def get_group_bindings():
    result = _service.get_group_bindings(
        subject_type=request.args.get("subjectType"),
        subject_id=request.args.get("subjectId"),
    )
    return ApiResponse.on_success(SuccessStatus.RBAC_BINDING_READ, result)


@rbac_bp.route("/group", methods=["DELETE"])
@jwt_required()
def delete_group_binding():
    subject_type = request.args.get("subjectType", "")
    subject_id   = request.args.get("subjectId", "")

    if not all([subject_type, subject_id]):
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "쿼리 파라미터(subjectType, subjectId)가 필요합니다.")

    try:
        _service.delete_binding(subject_type, subject_id)
        return ApiResponse.on_success(SuccessStatus.RBAC_BINDING_DELETE)
    except ValueError as e:
        return _handle(e)
