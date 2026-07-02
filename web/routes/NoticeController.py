from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from core.response.ApiResponse import ApiResponse
from core.response.ErrorStatus import ErrorStatus
from core.response.SuccessStatus import SuccessStatus
from core.jwt.JwtUtils import role_required
from service.NoticeService.NoticeService import NoticeService
from domain.model.Member import Member

notice_bp = Blueprint("notice", __name__, url_prefix="/api/notices")
_service = NoticeService()


def _notice_to_dict(notice):
    return {
        "noticeId":   notice.id,
        "memberId":   notice.member_id,
        "title":      notice.title,
        "content":    notice.content,
        "viewCount":  notice.view_count,
        "isPinned":   notice.is_pinned,
        "createdAt":  notice.created_at.isoformat(),
        "updatedAt":  notice.updated_at.isoformat(),
    }


@notice_bp.route("", methods=["GET"])
@jwt_required()
def get_notices():
    """공지사항 목록 조회"""
    notices = _service.get_all()
    return ApiResponse.on_success(
        SuccessStatus._OK,
        [_notice_to_dict(n) for n in notices]
    )


@notice_bp.route("/<notice_id>", methods=["GET"])
@jwt_required()
def get_notice(notice_id):
    """공지사항 상세 조회"""
    try:
        notice = _service.get_one_for_view(notice_id)
        return ApiResponse.on_success(SuccessStatus._OK, _notice_to_dict(notice))
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._NOT_FOUND, str(e))


@notice_bp.route("", methods=["POST"])
@jwt_required()
@role_required("ADMIN", "SUPERADMIN")
def create_notice():

    data      = request.get_json(silent=True) or {}
    title     = data.get("title", "").strip()
    content   = data.get("content", "").strip()
    is_pinned = bool(data.get("isPinned", False))

    if not title or not content:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "제목과 내용을 입력해주세요.")

    account_id = get_jwt_identity()
    member = Member.query.filter_by(account_id=account_id).first()
    if member is None:
        return ApiResponse.on_failure(ErrorStatus._NOT_FOUND, "사용자를 찾을 수 없습니다.")

    notice = _service.create(member.id, title, content, is_pinned)
    return ApiResponse.on_success(SuccessStatus._OK, _notice_to_dict(notice))


@notice_bp.route("/<notice_id>", methods=["PUT"])
@jwt_required()
@role_required("ADMIN", "SUPERADMIN")
def update_notice(notice_id):

    data      = request.get_json(silent=True) or {}
    title     = data.get("title", "").strip()
    content   = data.get("content", "").strip()
    is_pinned = bool(data.get("isPinned", False))

    if not title or not content:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "제목과 내용을 입력해주세요.")

    try:
        notice = _service.update(notice_id, title, content, is_pinned)
        return ApiResponse.on_success(SuccessStatus._OK, _notice_to_dict(notice))
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._NOT_FOUND, str(e))


@notice_bp.route("/<notice_id>", methods=["DELETE"])
@jwt_required()
@role_required("ADMIN", "SUPERADMIN")
def delete_notice(notice_id):

    try:
        _service.delete(notice_id)
        return ApiResponse.on_success(SuccessStatus._OK, None)
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._NOT_FOUND, str(e))