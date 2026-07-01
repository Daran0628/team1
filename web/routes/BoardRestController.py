from flask import Blueprint, request, Response
from urllib.parse import quote as _urlquote
from flask_jwt_extended import jwt_required

from core.response.ApiResponse import ApiResponse
from core.response.ErrorStatus import ErrorStatus
from core.response.SuccessStatus import SuccessStatus
from service.BoardService.BoardService import (
    BoardException,
    list_boards,
    create_board,
    get_board,
    update_board,
    delete_board,
    list_posts,
    create_post,
    get_post,
    update_post,
    delete_post,
    approve_post,
    reject_post,
    toggle_like,
    list_comments,
    create_comment,
    update_comment,
    delete_comment,
    list_approvers,
    add_approver,
    remove_approver,
    upload_attachments,
    list_attachments,
    get_attachment_url,
    stream_attachment,
    render_post_content,
    delete_attachment,
)

board_bp = Blueprint("board", __name__, url_prefix="/api/board")


def _handle(fn):
    """공통 예외 처리 래퍼."""
    try:
        return fn()
    except BoardException as e:
        return ApiResponse.on_failure(e.error_status)
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, str(e))
    except Exception as e:
        return ApiResponse.on_failure(ErrorStatus._INTERNAL_SERVER_ERROR, str(e))


# ── Board ────────────────────────────────────────────────────

@board_bp.route("/boards", methods=["GET"])
@jwt_required()
def api_list_boards():
    """접근 가능한 게시판 목록 조회."""
    def work():
        return ApiResponse.on_success(SuccessStatus.BOARD_READ, list_boards())
    return _handle(work)


@board_bp.route("/boards", methods=["POST"])
@jwt_required()
def api_create_board():
    """게시판 생성 (관리자 전용)."""
    body = request.get_json(silent=True) or {}
    def work():
        return ApiResponse.on_success(SuccessStatus.BOARD_CREATE, create_board(body))
    return _handle(work)


@board_bp.route("/boards/<board_id>", methods=["GET"])
@jwt_required()
def api_get_board(board_id: str):
    """게시판 단건 조회."""
    def work():
        return ApiResponse.on_success(SuccessStatus.BOARD_READ, get_board(board_id))
    return _handle(work)


@board_bp.route("/boards/<board_id>", methods=["PUT"])
@jwt_required()
def api_update_board(board_id: str):
    """게시판 정보 수정 (관리자 전용)."""
    body = request.get_json(silent=True) or {}
    def work():
        return ApiResponse.on_success(SuccessStatus.BOARD_UPDATE, update_board(board_id, body))
    return _handle(work)


@board_bp.route("/boards/<board_id>", methods=["DELETE"])
@jwt_required()
def api_delete_board(board_id: str):
    """게시판 삭제 (관리자 전용)."""
    def work():
        delete_board(board_id)
        return ApiResponse.on_success(SuccessStatus.BOARD_DELETE)
    return _handle(work)


# ── Post ─────────────────────────────────────────────────────

@board_bp.route("/boards/<board_id>/posts", methods=["GET"])
@jwt_required()
def api_list_posts(board_id: str):
    """게시글 목록 조회. ?page=1&size=20"""
    page = max(1, int(request.args.get("page", 1)))
    size = min(100, max(1, int(request.args.get("size", 20))))
    def work():
        return ApiResponse.on_success(SuccessStatus.POST_READ, list_posts(board_id, page, size))
    return _handle(work)


@board_bp.route("/boards/<board_id>/posts", methods=["POST"])
@jwt_required()
def api_create_post(board_id: str):
    """게시글 작성. 승인 필요 게시판은 PENDING 상태로 생성."""
    body = request.get_json(silent=True) or {}
    def work():
        return ApiResponse.on_success(SuccessStatus.POST_CREATE, create_post(board_id, body))
    return _handle(work)


@board_bp.route("/boards/<board_id>/posts/<post_id>", methods=["GET"])
@jwt_required()
def api_get_post(board_id: str, post_id: str):
    """게시글 상세 조회 (조회수 증가 포함)."""
    def work():
        return ApiResponse.on_success(SuccessStatus.POST_READ, get_post(board_id, post_id))
    return _handle(work)


@board_bp.route("/boards/<board_id>/posts/<post_id>", methods=["PUT"])
@jwt_required()
def api_update_post(board_id: str, post_id: str):
    """게시글 수정 (작성자 또는 관리자)."""
    body = request.get_json(silent=True) or {}
    def work():
        return ApiResponse.on_success(SuccessStatus.POST_UPDATE, update_post(board_id, post_id, body))
    return _handle(work)


@board_bp.route("/boards/<board_id>/posts/<post_id>", methods=["DELETE"])
@jwt_required()
def api_delete_post(board_id: str, post_id: str):
    """게시글 삭제 (작성자 또는 관리자)."""
    def work():
        delete_post(board_id, post_id)
        return ApiResponse.on_success(SuccessStatus.POST_DELETE)
    return _handle(work)


@board_bp.route("/boards/<board_id>/posts/<post_id>/approve", methods=["PATCH"])
@jwt_required()
def api_approve_post(board_id: str, post_id: str):
    """PENDING 게시글을 승인 (승인자 또는 관리자)."""
    def work():
        return ApiResponse.on_success(SuccessStatus.POST_APPROVE, approve_post(board_id, post_id))
    return _handle(work)


@board_bp.route("/boards/<board_id>/posts/<post_id>/reject", methods=["PATCH"])
@jwt_required()
def api_reject_post(board_id: str, post_id: str):
    """PENDING 게시글을 반려 (승인자 또는 관리자)."""
    def work():
        return ApiResponse.on_success(SuccessStatus.POST_REJECT, reject_post(board_id, post_id))
    return _handle(work)


@board_bp.route("/boards/<board_id>/posts/<post_id>/like", methods=["POST"])
@jwt_required()
def api_toggle_like(board_id: str, post_id: str):
    """게시글 추천 토글."""
    def work():
        return ApiResponse.on_success(SuccessStatus.POST_LIKE, toggle_like(board_id, post_id))
    return _handle(work)


# ── Comment ──────────────────────────────────────────────────

@board_bp.route("/boards/<board_id>/posts/<post_id>/comments", methods=["GET"])
@jwt_required()
def api_list_comments(board_id: str, post_id: str):
    """댓글 목록 조회 (대댓글 포함)."""
    def work():
        return ApiResponse.on_success(SuccessStatus.COMMENT_READ, list_comments(board_id, post_id))
    return _handle(work)


@board_bp.route("/boards/<board_id>/posts/<post_id>/comments", methods=["POST"])
@jwt_required()
def api_create_comment(board_id: str, post_id: str):
    """댓글 또는 대댓글 작성. body: {content, parentId?}"""
    body = request.get_json(silent=True) or {}
    def work():
        return ApiResponse.on_success(SuccessStatus.COMMENT_CREATE, create_comment(board_id, post_id, body))
    return _handle(work)


@board_bp.route("/boards/<board_id>/posts/<post_id>/comments/<comment_id>", methods=["PUT"])
@jwt_required()
def api_update_comment(board_id: str, post_id: str, comment_id: str):
    """댓글 수정 (작성자 또는 관리자)."""
    body = request.get_json(silent=True) or {}
    def work():
        return ApiResponse.on_success(SuccessStatus.COMMENT_UPDATE, update_comment(board_id, post_id, comment_id, body))
    return _handle(work)


@board_bp.route("/boards/<board_id>/posts/<post_id>/comments/<comment_id>", methods=["DELETE"])
@jwt_required()
def api_delete_comment(board_id: str, post_id: str, comment_id: str):
    """댓글 삭제 (작성자 또는 관리자)."""
    def work():
        delete_comment(board_id, post_id, comment_id)
        return ApiResponse.on_success(SuccessStatus.COMMENT_DELETE)
    return _handle(work)


# ── 첨부파일 ─────────────────────────────────────────────────

@board_bp.route("/boards/<board_id>/posts/<post_id>/attachments", methods=["POST"])
@jwt_required()
def api_upload_attachments(board_id: str, post_id: str):
    """파일 첨부 업로드. multipart/form-data, field name: 'files' (복수 선택 가능).
    이미지·문서 등 타입 제한 없이 여러 파일 동시 업로드 지원."""
    def work():
        files = request.files.getlist("files")
        if not files or all(f.filename == "" for f in files):
            return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "files 필드에 파일을 첨부해주세요.")
        result = upload_attachments(board_id, post_id, [f for f in files if f.filename])
        return ApiResponse.on_success(SuccessStatus.ATTACHMENT_UPLOAD, result)
    return _handle(work)


@board_bp.route("/boards/<board_id>/posts/<post_id>/attachments", methods=["GET"])
@jwt_required()
def api_list_attachments(board_id: str, post_id: str):
    """첨부파일 목록 조회."""
    def work():
        return ApiResponse.on_success(SuccessStatus.ATTACHMENT_READ, list_attachments(board_id, post_id))
    return _handle(work)


@board_bp.route("/boards/<board_id>/posts/<post_id>/attachments/<attachment_id>/url", methods=["GET"])
@jwt_required()
def api_get_attachment_url(board_id: str, post_id: str, attachment_id: str):
    """첨부파일 presigned 다운로드 URL 발급. ?expires=3600 (초 단위, 기본 1시간)"""
    expires = max(60, min(86400, int(request.args.get("expires", 3600))))
    def work():
        url = get_attachment_url(board_id, post_id, attachment_id, expires)
        return ApiResponse.on_success(SuccessStatus.ATTACHMENT_URL, {"url": url, "expires": expires})
    return _handle(work)


@board_bp.route("/boards/<board_id>/posts/<post_id>/attachments/<attachment_id>", methods=["DELETE"])
@jwt_required()
def api_delete_attachment(board_id: str, post_id: str, attachment_id: str):
    """첨부파일 삭제 (작성자 또는 관리자)."""
    def work():
        delete_attachment(board_id, post_id, attachment_id)
        return ApiResponse.on_success(SuccessStatus.ATTACHMENT_DELETE)
    return _handle(work)


@board_bp.route("/boards/<board_id>/posts/<post_id>/attachments/<attachment_id>/inline", methods=["GET"])
@jwt_required()
def api_inline_attachment(board_id: str, post_id: str, attachment_id: str):
    """첨부파일 바이너리 직접 반환 (이미지 인라인 로드용).
    Authorization 헤더를 보낼 수 없는 <img> 태그에서는
    프론트에서 fetch → blob URL 변환 후 사용:
      const res = await apiFetch('/api/board/.../inline');
      const blob = await res.blob();
      img.src = URL.createObjectURL(blob);
    만료 없음 — presigned URL과 달리 세션이 유효하면 항상 접근 가능."""
    try:
        data, content_type, filename = stream_attachment(board_id, post_id, attachment_id)
        return Response(
            data,
            mimetype=content_type,
            headers={
                "Content-Disposition": f"inline; filename*=UTF-8''{_urlquote(filename)}",
                "Cache-Control": "private, max-age=3600",
            },
        )
    except Exception as e:
        from core.response.ErrorStatus import ErrorStatus as ES
        from service.BoardService.BoardService import BoardException as BE
        if isinstance(e, BE):
            return ApiResponse.on_failure(e.error_status)
        return ApiResponse.on_failure(ES._INTERNAL_SERVER_ERROR, str(e))


@board_bp.route("/boards/<board_id>/posts/<post_id>/rendered", methods=["GET"])
@jwt_required()
def api_rendered_content(board_id: str, post_id: str):
    """본문 내 {{ATTACHMENT:id}} 플레이스홀더를 presigned URL로 치환한 content 반환.
    리치 에디터에서 이미지를 {{ATTACHMENT:uuid}} 형식으로 저장했을 때 사용."""
    def work():
        content = render_post_content(board_id, post_id)
        return ApiResponse.on_success(SuccessStatus.POST_READ, {"content": content})
    return _handle(work)


# ── 게시판 승인자 관리 ────────────────────────────────────────

@board_bp.route("/boards/<board_id>/approvers", methods=["GET"])
@jwt_required()
def api_list_approvers(board_id: str):
    """게시판 승인자 목록 조회 (관리자 전용)."""
    def work():
        return ApiResponse.on_success(SuccessStatus.BOARD_APPROVER_READ, list_approvers(board_id))
    return _handle(work)


@board_bp.route("/boards/<board_id>/approvers", methods=["POST"])
@jwt_required()
def api_add_approver(board_id: str):
    """게시판 승인자 추가 (관리자 전용). body: {memberId}"""
    body = request.get_json(silent=True) or {}
    def work():
        member_id = body.get("memberId", "").strip()
        if not member_id:
            return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "memberId는 필수입니다.")
        return ApiResponse.on_success(SuccessStatus.BOARD_APPROVER_ADD, add_approver(board_id, member_id))
    return _handle(work)


@board_bp.route("/boards/<board_id>/approvers/<member_id>", methods=["DELETE"])
@jwt_required()
def api_remove_approver(board_id: str, member_id: str):
    """게시판 승인자 제거 (관리자 전용)."""
    def work():
        remove_approver(board_id, member_id)
        return ApiResponse.on_success(SuccessStatus.BOARD_APPROVER_REMOVE)
    return _handle(work)
