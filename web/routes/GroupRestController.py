import logging

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from core.response.ApiResponse import ApiResponse
from core.response.ErrorStatus import ErrorStatus
from core.response.SuccessStatus import SuccessStatus
from service.GroupService.GroupService import GroupService
from web.dto.GroupRequestDTO import (
    AddGroupMembersRequestDTO,
    CreateGroupRequestDTO,
    RemoveGroupMembersRequestDTO,
    UpdateGroupRequestDTO,
)

logger = logging.getLogger(__name__)

group_bp = Blueprint("group", __name__, url_prefix="/api/group")
_service = GroupService()

_ERR_MAP = {
    "GROUP_NOT_FOUND":           ErrorStatus.GROUP_NOT_FOUND,
    "GROUP_NAME_DUPLICATE":      ErrorStatus.GROUP_NAME_DUPLICATE,
    "GROUP_MEMBER_NOT_FOUND":    ErrorStatus.GROUP_MEMBER_NOT_FOUND,
    "GROUP_MEMBER_ALREADY_EXISTS": ErrorStatus.GROUP_MEMBER_ALREADY_EXISTS,
}


def _handle(exc: Exception):
    return ApiResponse.on_failure(_ERR_MAP.get(str(exc), ErrorStatus._INTERNAL_SERVER_ERROR))


# ──────────────────────────────────────────────
# /api/group  — Group CRUD
# ──────────────────────────────────────────────

@group_bp.route("", methods=["POST"])
@jwt_required()
def create_group():
    data = request.get_json(silent=True) or {}
    try:
        dto = CreateGroupRequestDTO(
            group_name=data.get("groupName", ""),
            description=data.get("description"),
            member_ids=data.get("memberIds") or [],
        )
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, str(e))

    try:
        result = _service.create_group(dto)
        return ApiResponse.on_success(SuccessStatus.GROUP_CREATE, result)
    except ValueError as e:
        return _handle(e)


@group_bp.route("", methods=["GET"])
@jwt_required()
def get_all_groups():
    return ApiResponse.on_success(SuccessStatus.GROUP_READ, _service.get_all_groups())


@group_bp.route("/<group_id>", methods=["GET"])
@jwt_required()
def get_group(group_id: str):
    try:
        return ApiResponse.on_success(SuccessStatus.GROUP_READ, _service.get_group(group_id))
    except ValueError as e:
        return _handle(e)


@group_bp.route("/<group_id>", methods=["PUT"])
@jwt_required()
def update_group(group_id: str):
    data = request.get_json(silent=True) or {}
    try:
        dto = UpdateGroupRequestDTO(
            group_name=data.get("groupName"),
            description=data.get("description"),
        )
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, str(e))

    try:
        result = _service.update_group(group_id, dto)
        return ApiResponse.on_success(SuccessStatus.GROUP_UPDATE, result)
    except ValueError as e:
        return _handle(e)


@group_bp.route("/<group_id>", methods=["DELETE"])
@jwt_required()
def delete_group(group_id: str):
    try:
        _service.delete_group(group_id)
        return ApiResponse.on_success(SuccessStatus.GROUP_DELETE)
    except ValueError as e:
        return _handle(e)


# ──────────────────────────────────────────────
# /api/group/<group_id>/member  — 멤버 추가/제거
# ──────────────────────────────────────────────

@group_bp.route("/<group_id>/member", methods=["POST"])
@jwt_required()
def add_members(group_id: str):
    data = request.get_json(silent=True) or {}
    try:
        dto = AddGroupMembersRequestDTO(member_ids=data.get("memberIds", []))
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, str(e))

    try:
        result = _service.add_members(group_id, dto)
        return ApiResponse.on_success(SuccessStatus.GROUP_MEMBER_ADD, result)
    except ValueError as e:
        return _handle(e)


@group_bp.route("/<group_id>/member", methods=["DELETE"])
@jwt_required()
def remove_members(group_id: str):
    data = request.get_json(silent=True) or {}
    try:
        dto = RemoveGroupMembersRequestDTO(member_ids=data.get("memberIds", []))
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, str(e))

    try:
        result = _service.remove_members(group_id, dto)
        return ApiResponse.on_success(SuccessStatus.GROUP_MEMBER_REMOVE, result)
    except ValueError as e:
        return _handle(e)


# ──────────────────────────────────────────────
# /api/group/members  — 전체 멤버 목록 (그룹 피커 용)
# ──────────────────────────────────────────────

@group_bp.route("/members", methods=["GET"])
@jwt_required()
def get_all_members():
    return ApiResponse.on_success(SuccessStatus.GROUP_READ, _service.get_all_members())


# ──────────────────────────────────────────────
# /api/group/department  — 부서 기반 멤버 조회 / 일괄 추가
# ──────────────────────────────────────────────

@group_bp.route("/department/<dept_id>/members", methods=["GET"])
@jwt_required()
def get_dept_members(dept_id: str):
    """해당 부서 소속 멤버 UUID 목록 조회 (그룹 추가 전 미리보기 용도)."""
    result = _service.get_members_by_dept(dept_id)
    return ApiResponse.on_success(SuccessStatus.GROUP_READ, result)


@group_bp.route("/<group_id>/member/department/<dept_id>", methods=["POST"])
@jwt_required()
def add_members_by_dept(group_id: str, dept_id: str):
    """특정 부서 소속 멤버 전체를 그룹에 일괄 추가. 이미 속한 멤버는 스킵."""
    try:
        result = _service.add_members_by_dept(group_id, dept_id)
        return ApiResponse.on_success(SuccessStatus.GROUP_MEMBER_ADD, result)
    except ValueError as e:
        return _handle(e)
