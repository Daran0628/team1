from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from core.response.ApiResponse import ApiResponse
from core.response.ErrorStatus import ErrorStatus
from core.response.SuccessStatus import SuccessStatus
from domain.model.Member import Member
from service.FaqService.FaqService import FaqService

faq_bp = Blueprint("faq", __name__, url_prefix="/api/faqs")
_service = FaqService()


def _faq_to_dict(faq):
    return {
        "faqId":     faq.id,
        "memberId":  faq.member_id,
        "question":  faq.question,
        "answer":    faq.answer,
        "category":  faq.category,
        "createdAt": faq.created_at.isoformat(),
        "updatedAt": faq.updated_at.isoformat(),
    }


@faq_bp.route("", methods=["GET"])
@jwt_required()
def get_faqs():
    """FAQ 목록 조회 (카테고리 필터 가능)"""
    category = request.args.get("category", None)
    faqs = _service.get_all(category=category)
    return ApiResponse.on_success(
        SuccessStatus._OK,
        [_faq_to_dict(f) for f in faqs]
    )


@faq_bp.route("/<faq_id>", methods=["GET"])
@jwt_required()
def get_faq(faq_id):
    """FAQ 단건 조회"""
    try:
        faq = _service.get_one(faq_id)
        return ApiResponse.on_success(SuccessStatus._OK, _faq_to_dict(faq))
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._NOT_FOUND, str(e))


@faq_bp.route("", methods=["POST"])
@jwt_required()
def create_faq():
    """FAQ 등록 (ADMIN, SUPERADMIN만)"""
    claims = get_jwt()
    if claims.get("role") not in ("ADMIN", "SUPERADMIN"):
        return ApiResponse.on_failure(ErrorStatus._FORBIDDEN)

    data     = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    answer   = data.get("answer", "").strip()
    category = data.get("category", "").strip() or None

    if not question or not answer:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "질문과 답변을 입력해주세요.")

    account_id = get_jwt_identity()
    member = Member.query.filter_by(account_id=account_id).first()
    if member is None:
        return ApiResponse.on_failure(ErrorStatus._NOT_FOUND, "사용자를 찾을 수 없습니다.")

    faq = _service.create(member.id, question, answer, category)
    return ApiResponse.on_success(SuccessStatus._OK, _faq_to_dict(faq))


@faq_bp.route("/<faq_id>", methods=["PUT"])
@jwt_required()
def update_faq(faq_id):
    """FAQ 수정 (ADMIN, SUPERADMIN만)"""
    claims = get_jwt()
    if claims.get("role") not in ("ADMIN", "SUPERADMIN"):
        return ApiResponse.on_failure(ErrorStatus._FORBIDDEN)

    data     = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    answer   = data.get("answer", "").strip()
    category = data.get("category", "").strip() or None

    if not question or not answer:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "질문과 답변을 입력해주세요.")

    try:
        faq = _service.update(faq_id, question, answer, category)
        return ApiResponse.on_success(SuccessStatus._OK, _faq_to_dict(faq))
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._NOT_FOUND, str(e))


@faq_bp.route("/<faq_id>", methods=["DELETE"])
@jwt_required()
def delete_faq(faq_id):
    """FAQ 삭제 (ADMIN, SUPERADMIN만)"""
    claims = get_jwt()
    if claims.get("role") not in ("ADMIN", "SUPERADMIN"):
        return ApiResponse.on_failure(ErrorStatus._FORBIDDEN)

    try:
        _service.delete(faq_id)
        return ApiResponse.on_success(SuccessStatus._OK, None)
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._NOT_FOUND, str(e))