from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from core.response.ApiResponse import ApiResponse
from core.response.ErrorStatus import ErrorStatus
from core.response.SuccessStatus import SuccessStatus
from domain.model.Member import Member
from service.TicketService.TicketService import TicketService

ticket_bp = Blueprint("ticket", __name__, url_prefix="/api/tickets")
_service = TicketService()


def _ticket_to_dict(ticket):
    return {
        "ticketId":     ticket.id,
        "ticketNo":     ticket.ticket_no,
        "memberId":     ticket.member_id,
        "assignedTo":   ticket.assigned_to,
        "assigneeName": ticket.assignee.name_ko if ticket.assignee else None,
        "title":        ticket.title,
        "content":      ticket.content,
        "status":       ticket.status,
        "priority":     ticket.priority,
        "createdAt":    ticket.created_at.isoformat(),
        "updatedAt":    ticket.updated_at.isoformat(),
    }


@ticket_bp.route("", methods=["GET"])
@jwt_required()
def get_tickets():
    """티켓 목록 (관리자: 전체, 일반유저: 내 것만)"""
    claims = get_jwt()
    role = claims.get("role")

    account_id = get_jwt_identity()
    member = Member.query.filter_by(account_id=account_id).first()

    if role in ("ADMIN", "SUPERADMIN"):
        tickets = _service.get_all()
    else:
        tickets = _service.get_my_tickets(member.id)

    return ApiResponse.on_success(
        SuccessStatus._OK,
        [_ticket_to_dict(t) for t in tickets]
    )


@ticket_bp.route("/<ticket_id>", methods=["GET"])
@jwt_required()
def get_ticket(ticket_id):
    """티켓 단건 조회"""
    try:
        ticket = _service.get_one(ticket_id)
        return ApiResponse.on_success(SuccessStatus._OK, _ticket_to_dict(ticket))
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._NOT_FOUND, str(e))


@ticket_bp.route("", methods=["POST"])
@jwt_required()
def create_ticket():
    """티켓 생성 (모든 로그인 유저)"""
    data     = request.get_json(silent=True) or {}
    title    = data.get("title", "").strip()
    content  = data.get("content", "").strip()
    priority = data.get("priority", "MEDIUM").strip()

    if not title or not content:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "제목과 내용을 입력해주세요.")

    account_id = get_jwt_identity()
    member = Member.query.filter_by(account_id=account_id).first()
    if member is None:
        return ApiResponse.on_failure(ErrorStatus._NOT_FOUND, "사용자를 찾을 수 없습니다.")

    ticket = _service.create(member.id, title, content, priority)
    return ApiResponse.on_success(SuccessStatus._OK, _ticket_to_dict(ticket))


@ticket_bp.route("/<ticket_id>/status", methods=["PUT"])
@jwt_required()
def update_ticket_status(ticket_id):
    """티켓 상태 변경 (관리자만)"""
    claims = get_jwt()
    if claims.get("role") not in ("ADMIN", "SUPERADMIN"):
        return ApiResponse.on_failure(ErrorStatus._FORBIDDEN)

    data   = request.get_json(silent=True) or {}
    status = data.get("status", "").strip()

    if status not in ("OPEN", "IN_PROGRESS", "PENDING", "RESOLVED", "CLOSED"):
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "올바른 상태값을 입력해주세요.")

    try:
        ticket = _service.update_status(ticket_id, status)
        return ApiResponse.on_success(SuccessStatus._OK, _ticket_to_dict(ticket))
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._NOT_FOUND, str(e))


@ticket_bp.route("/<ticket_id>/assign", methods=["PUT"])
@jwt_required()
def assign_ticket(ticket_id):
    """티켓 담당자 배정 (관리자만)"""
    claims = get_jwt()
    if claims.get("role") not in ("ADMIN", "SUPERADMIN"):
        return ApiResponse.on_failure(ErrorStatus._FORBIDDEN)

    data = request.get_json(silent=True) or {}
    assigned_to = data.get("assignedTo", "").strip()

    if not assigned_to:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "담당자를 입력해주세요.")

    try:
        ticket = _service.assign(ticket_id, assigned_to)
        return ApiResponse.on_success(SuccessStatus._OK, _ticket_to_dict(ticket))
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._NOT_FOUND, str(e))


@ticket_bp.route("/<ticket_id>", methods=["DELETE"])
@jwt_required()
def delete_ticket(ticket_id):
    """티켓 삭제 (관리자만)"""
    claims = get_jwt()
    if claims.get("role") not in ("ADMIN", "SUPERADMIN"):
        return ApiResponse.on_failure(ErrorStatus._FORBIDDEN)

    try:
        _service.delete(ticket_id)
        return ApiResponse.on_success(SuccessStatus._OK, None)
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._NOT_FOUND, str(e))


@ticket_bp.route("/notify/count", methods=["GET"])
@jwt_required()
def get_notify_count():
    """관리자 알림 카운트 조회"""
    claims = get_jwt()
    if claims.get("role") not in ("ADMIN", "SUPERADMIN"):
        return ApiResponse.on_failure(ErrorStatus._FORBIDDEN)
    count = _service.get_notify_count()
    return ApiResponse.on_success(SuccessStatus._OK, {"count": count})


@ticket_bp.route("/notify/clear", methods=["POST"])
@jwt_required()
def clear_notify_count():
    """관리자 알림 카운트 초기화"""
    claims = get_jwt()
    if claims.get("role") not in ("ADMIN", "SUPERADMIN"):
        return ApiResponse.on_failure(ErrorStatus._FORBIDDEN)
    _service.clear_notify_count()
    return ApiResponse.on_success(SuccessStatus._OK, {"message": "알림 초기화 완료"})