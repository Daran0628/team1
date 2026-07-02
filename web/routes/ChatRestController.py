import logging

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from core.response.ApiResponse import ApiResponse
from core.response.ErrorStatus import ErrorStatus
from core.response.SuccessStatus import SuccessStatus
from domain.model.Member import Member
from service.ChatService.ChatService import ChatService
from web.dto.ChatRequestDTO import (
    AddRoomMembersRequestDTO,
    CreateRoomRequestDTO,
    LeaveRoomRequestDTO,
    SendMessageRequestDTO,
)

_FILE_ERR_MAP = {
    "CHAT_FILE_NOT_FOUND":     ErrorStatus.CHAT_FILE_NOT_FOUND,
    "CHAT_FILE_UPLOAD_FAILED": ErrorStatus.CHAT_FILE_UPLOAD_FAILED,
    "CHAT_FILE_TOO_LARGE":     ErrorStatus.CHAT_FILE_TOO_LARGE,
}

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")
_service = ChatService()

_ERR_MAP = {
    "CHAT_ROOM_NOT_FOUND":        ErrorStatus.CHAT_ROOM_NOT_FOUND,
    "CHAT_NOT_A_MEMBER":          ErrorStatus.CHAT_NOT_A_MEMBER,
    "CHAT_ALREADY_A_MEMBER":      ErrorStatus.CHAT_ALREADY_A_MEMBER,
    "CHAT_DIRECT_ALREADY_EXISTS": ErrorStatus.CHAT_DIRECT_ALREADY_EXISTS,
    "CHAT_PERMISSION_DENIED":     ErrorStatus.CHAT_PERMISSION_DENIED,
    "CHAT_ADMIN_MUST_TRANSFER":   ErrorStatus.CHAT_ADMIN_MUST_TRANSFER,
    "CHAT_MESSAGE_NOT_FOUND":     ErrorStatus.CHAT_MESSAGE_NOT_FOUND,
}


def _handle(exc: Exception):
    code = str(exc)
    status = _ERR_MAP.get(code) or _FILE_ERR_MAP.get(code) or ErrorStatus._INTERNAL_SERVER_ERROR
    return ApiResponse.on_failure(status)


def _current_member_id() -> str:
    """JWT identity(account_id) → member UUID 변환.
    get_jwt_identity()는 account_id를 반환하므로 DB에서 실제 member_id를 조회한다.
    """
    account_id = get_jwt_identity()
    member = Member.query.filter_by(account_id=account_id).first()
    if not member:
        raise ValueError("CHAT_NOT_A_MEMBER")
    return member.id


# ── 멤버 전체 목록 (채팅 피커용 — RBAC 불필요) ───────────────────

@chat_bp.route("/members", methods=["GET"])
@jwt_required()
def get_chat_members():
    """채팅방 생성/초대 피커용 전체 멤버 목록. JWT 인증만 요구한다."""
    members = Member.query.order_by(Member.name_ko).all()
    result = [
        {"member_id": m.id, "account_id": m.account_id, "name_ko": m.name_ko}
        for m in members
    ]
    return ApiResponse.on_success(SuccessStatus.CHAT_ROOM_READ, result)


# ── 채팅방 CRUD ─────────────────────────────────────────────────

@chat_bp.route("/rooms", methods=["POST"])
@jwt_required()
def create_room():
    try:
        member_id = _current_member_id()
    except ValueError as e:
        return _handle(e)
    data = request.get_json(silent=True) or {}
    try:
        dto = CreateRoomRequestDTO(
            room_type=data.get("roomType", ""),
            member_ids=data.get("memberIds") or [],
            room_name=data.get("roomName"),
        )
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, str(e))

    try:
        result = _service.create_room(member_id, dto)
        return ApiResponse.on_success(SuccessStatus.CHAT_ROOM_CREATE, result)
    except ValueError as e:
        return _handle(e)


@chat_bp.route("/rooms", methods=["GET"])
@jwt_required()
def get_my_rooms():
    try:
        member_id = _current_member_id()
    except ValueError as e:
        return _handle(e)
    return ApiResponse.on_success(SuccessStatus.CHAT_ROOM_READ, _service.get_my_rooms(member_id))


@chat_bp.route("/rooms/<room_id>", methods=["GET"])
@jwt_required()
def get_room(room_id: str):
    try:
        member_id = _current_member_id()
        result = _service.get_room(room_id, member_id)
        return ApiResponse.on_success(SuccessStatus.CHAT_ROOM_READ, result)
    except ValueError as e:
        return _handle(e)


@chat_bp.route("/rooms/<room_id>/leave", methods=["POST"])
@jwt_required()
def leave_room(room_id: str):
    try:
        member_id = _current_member_id()
    except ValueError as e:
        return _handle(e)
    data = request.get_json(silent=True) or {}
    new_admin_id = data.get("newAdminId") or None
    try:
        _service.leave_room(room_id, member_id, new_admin_id)
        return ApiResponse.on_success(SuccessStatus.CHAT_ROOM_LEAVE)
    except ValueError as e:
        return _handle(e)


# ── 멤버 관리 ───────────────────────────────────────────────────

@chat_bp.route("/rooms/<room_id>/members", methods=["POST"])
@jwt_required()
def add_members(room_id: str):
    try:
        member_id = _current_member_id()
    except ValueError as e:
        return _handle(e)
    data = request.get_json(silent=True) or {}
    try:
        dto = AddRoomMembersRequestDTO(member_ids=data.get("memberIds", []))
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, str(e))

    try:
        result = _service.add_members(room_id, member_id, dto)
        return ApiResponse.on_success(SuccessStatus.CHAT_MEMBER_ADD, result)
    except ValueError as e:
        return _handle(e)


@chat_bp.route("/rooms/<room_id>/members/<target_id>", methods=["DELETE"])
@jwt_required()
def remove_member(room_id: str, target_id: str):
    try:
        member_id = _current_member_id()
        result = _service.remove_member(room_id, member_id, target_id)
        return ApiResponse.on_success(SuccessStatus.CHAT_MEMBER_REMOVE, result)
    except ValueError as e:
        return _handle(e)


# ── 메시지 ──────────────────────────────────────────────────────

@chat_bp.route("/rooms/<room_id>/messages", methods=["POST"])
@jwt_required()
def send_message(room_id: str):
    try:
        member_id = _current_member_id()
    except ValueError as e:
        return _handle(e)
    data = request.get_json(silent=True) or {}
    try:
        dto = SendMessageRequestDTO(
            message_type=data.get("messageType", ""),
            content=data.get("content"),
        )
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, str(e))

    try:
        result = _service.send_message(room_id, member_id, dto)
        return ApiResponse.on_success(SuccessStatus.CHAT_MESSAGE_SEND, result)
    except ValueError as e:
        return _handle(e)


@chat_bp.route("/rooms/<room_id>/messages", methods=["GET"])
@jwt_required()
def get_messages(room_id: str):
    try:
        member_id = _current_member_id()
    except ValueError as e:
        return _handle(e)
    since = request.args.get("since")
    limit = int(request.args.get("limit", 50))
    try:
        result = _service.get_messages(room_id, member_id, since, limit)
        return ApiResponse.on_success(SuccessStatus.CHAT_MESSAGE_READ, result)
    except ValueError as e:
        return _handle(e)


@chat_bp.route("/rooms/<room_id>/read", methods=["PUT"])
@jwt_required()
def mark_read(room_id: str):
    try:
        member_id = _current_member_id()
        _service.mark_read(room_id, member_id)
        return ApiResponse.on_success(SuccessStatus.CHAT_READ_MARKED)
    except ValueError as e:
        return _handle(e)


# ── 파일 / 이미지 첨부 ──────────────────────────────────────────

@chat_bp.route("/rooms/<room_id>/files", methods=["POST"])
@jwt_required()
def upload_file(room_id: str):
    """multipart/form-data, 'file' 필드로 파일 전송."""
    try:
        member_id = _current_member_id()
    except ValueError as e:
        return _handle(e)
    if "file" not in request.files:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "file 필드가 없습니다.")
    try:
        result = _service.upload_file(room_id, member_id, request.files["file"])
        return ApiResponse.on_success(SuccessStatus.CHAT_FILE_UPLOAD, result)
    except ValueError as e:
        return _handle(e)


@chat_bp.route("/rooms/<room_id>/files/<file_id>/url", methods=["GET"])
@jwt_required()
def get_file_url(room_id: str, file_id: str):
    """첨부 파일의 presigned 다운로드 URL 반환. ?expires=초 (기본 3600)."""
    try:
        member_id = _current_member_id()
    except ValueError as e:
        return _handle(e)
    expires = int(request.args.get("expires", 3600))
    try:
        url = _service.get_file_url(room_id, member_id, file_id, expires)
        return ApiResponse.on_success(SuccessStatus.CHAT_FILE_URL, {"url": url})
    except ValueError as e:
        return _handle(e)
