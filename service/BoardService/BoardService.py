import io
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from flask_jwt_extended import get_jwt_identity, get_jwt
from minio import S3Error

from core.config.MinioConfig import get_minio_client
from core.response.ErrorStatus import ErrorStatus
from domain.enum.PostStatus import PostStatus
from domain.model.Board import Board, Post, PostAttachment, PostComment, PostLike, PostView, BoardApprover
from domain.model.Member import Member
from extensions import db

logger = logging.getLogger(__name__)

BOARD_BUCKET = "board-files"


def ensure_board_bucket() -> None:
    """앱 시작 시 board-files 버킷이 없으면 MinIO에 생성한다."""
    from domain.model.StorageBucket import StorageBucket
    client = get_minio_client()
    if not StorageBucket.query.filter_by(bucket_name=BOARD_BUCKET).first():
        try:
            if not client.bucket_exists(BOARD_BUCKET):
                client.make_bucket(BOARD_BUCKET)
        except S3Error as e:
            logger.error("board-files 버킷 생성 실패: %s", e)
            return
        db.session.add(StorageBucket(bucket_name=BOARD_BUCKET, created_by="system"))
        db.session.commit()
        logger.info("board-files 버킷 생성 완료")


class BoardException(Exception):
    """게시판 관련 비즈니스 예외"""

    def __init__(self, error_status: ErrorStatus, message: str = None):
        self.error_status = error_status
        self.message = message or error_status.message
        super().__init__(self.message)


# ── 내부 헬퍼 ────────────────────────────────────────────────

def _current_member() -> Member:
    """JWT identity로 현재 멤버를 조회한다."""
    account_id = get_jwt_identity()
    member = Member.query.filter_by(account_id=account_id).first()
    if not member:
        raise BoardException(ErrorStatus._UNAUTHORIZED)
    return member


def _is_admin() -> bool:
    """JWT claims의 role이 ADMIN/SUPERADMIN인지 확인한다."""
    return get_jwt().get("role", "") in ("ADMIN", "SUPERADMIN")


def _assert_board_readable(board: Board, member: Member) -> None:
    """비공개 부서 게시판 접근 권한을 검증한다."""
    if not board.is_public and board.department_id != member.department_id:
        raise BoardException(ErrorStatus.BOARD_ACCESS_DENIED)


def _get_board_or_raise(board_id: str) -> Board:
    """board_id로 활성 게시판을 조회하고 없으면 예외를 발생시킨다."""
    board = Board.query.filter_by(id=board_id, is_active=True).first()
    if not board:
        raise BoardException(ErrorStatus.BOARD_NOT_FOUND)
    return board


def _get_post_or_raise(board_id: str, post_id: str) -> Post:
    """게시글을 조회하고 없거나 삭제된 경우 예외를 발생시킨다."""
    post = Post.query.filter_by(id=post_id, board_id=board_id, is_deleted=False).first()
    if not post:
        raise BoardException(ErrorStatus.POST_NOT_FOUND)
    return post


def _is_approver(board_id: str, member_id: str) -> bool:
    """해당 게시판의 승인자 여부를 반환한다."""
    return BoardApprover.query.filter_by(board_id=board_id, member_id=member_id).first() is not None


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    """ISO 8601 문자열을 datetime으로 변환한다. 파싱 실패 시 None 반환."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


# ── Board CRUD ───────────────────────────────────────────────

def list_boards() -> list:
    """접근 가능한 게시판 목록을 반환한다. 부서 게시판은 소속 부서원만 포함."""
    member = _current_member()
    boards = Board.query.filter_by(is_active=True).all()
    return [
        _board_to_dict(b) for b in boards
        if b.is_public or b.department_id == member.department_id
    ]


def create_board(data: dict) -> dict:
    """새 게시판을 생성한다. 관리자만 호출 가능."""
    if not _is_admin():
        raise BoardException(ErrorStatus.BOARD_ACCESS_DENIED)

    member = _current_member()
    board_name = data.get("boardName", "").strip()
    if not board_name:
        raise ValueError("boardName은 필수입니다.")

    from domain.enum.BoardType import BoardType
    type_str = data.get("boardType", "FREE")
    try:
        board_type = BoardType(type_str)
    except ValueError:
        raise ValueError(f"유효하지 않은 boardType: {type_str}")

    # 부서 게시판은 기본적으로 비공개
    is_public = data.get("isPublic", board_type != BoardType.Department)

    board = Board(
        board_name=board_name,
        board_type=board_type,
        description=data.get("description"),
        department_id=data.get("departmentId"),
        is_active=True,
        is_public=bool(is_public),
        requires_approval=bool(data.get("requiresApproval", False)),
        approval_expires_at=_parse_dt(data.get("approvalExpiresAt")),
        approval_purpose=data.get("approvalPurpose"),
        created_by=member.id,
    )
    try:
        db.session.add(board)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    return _board_to_dict(board)


def get_board(board_id: str) -> dict:
    """게시판 단건을 조회한다."""
    member = _current_member()
    board = _get_board_or_raise(board_id)
    _assert_board_readable(board, member)
    return _board_to_dict(board)


def update_board(board_id: str, data: dict) -> dict:
    """게시판 정보를 수정한다. 관리자만 호출 가능."""
    if not _is_admin():
        raise BoardException(ErrorStatus.BOARD_ACCESS_DENIED)

    board = _get_board_or_raise(board_id)
    if "boardName" in data:
        board.board_name = data["boardName"].strip()
    if "description" in data:
        board.description = data["description"]
    if "isActive" in data:
        board.is_active = bool(data["isActive"])
    if "requiresApproval" in data:
        board.requires_approval = bool(data["requiresApproval"])
    if "approvalExpiresAt" in data:
        board.approval_expires_at = _parse_dt(data["approvalExpiresAt"])
    if "approvalPurpose" in data:
        board.approval_purpose = data["approvalPurpose"]
    if "isPublic" in data:
        board.is_public = bool(data["isPublic"])

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    return _board_to_dict(board)


def delete_board(board_id: str) -> None:
    """게시판을 비활성화(소프트 삭제)한다. 관리자만 호출 가능."""
    if not _is_admin():
        raise BoardException(ErrorStatus.BOARD_ACCESS_DENIED)

    board = _get_board_or_raise(board_id)
    board.is_active = False
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e


# ── Post CRUD ────────────────────────────────────────────────

def list_posts(board_id: str, page: int = 1, size: int = 20) -> dict:
    """게시글 목록을 페이지네이션으로 반환한다."""
    member = _current_member()
    board = _get_board_or_raise(board_id)
    _assert_board_readable(board, member)

    q = Post.query.filter_by(board_id=board_id, is_deleted=False)

    # 승인 대기 글은 작성자·승인자·관리자만 조회 가능
    if not _is_admin() and not _is_approver(board_id, member.id):
        q = q.filter(
            db.or_(Post.status == PostStatus.Published, Post.author_id == member.id)
        )

    total = q.count()
    posts = (
        q.order_by(Post.is_pinned.desc(), Post.created_at.desc())
         .offset((page - 1) * size)
         .limit(size)
         .all()
    )
    # N+1 방지: 작성자 일괄 조회
    author_ids = list({p.author_id for p in posts})
    authors    = {m.id: m for m in Member.query.filter(Member.id.in_(author_ids)).all()} if author_ids else {}
    return {"total": total, "page": page, "size": size, "items": [_post_to_dict(p, authors.get(p.author_id)) for p in posts]}


def create_post(board_id: str, data: dict) -> dict:
    """게시글을 작성한다. 승인 필요 게시판은 PENDING 상태로 생성."""
    member = _current_member()
    board = _get_board_or_raise(board_id)
    _assert_board_readable(board, member)

    title = data.get("title", "").strip()
    content = data.get("content", "")
    if not title:
        raise ValueError("title은 필수입니다.")
    if not content:
        raise ValueError("content는 필수입니다.")

    # 승인 기간이 만료되었거나 승인자·관리자면 바로 게시
    approval_expired = (
        board.approval_expires_at
        and board.approval_expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc)
    )
    if board.requires_approval and not _is_admin() and not _is_approver(board_id, member.id) and not approval_expired:
        status = PostStatus.Pending
    else:
        status = PostStatus.Published

    post = Post(
        board_id=board_id,
        title=title,
        content=content,
        author_id=member.id,
        status=status,
        is_pinned=bool(data.get("isPinned", False)) and _is_admin(),
    )
    try:
        db.session.add(post)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    return _post_detail_to_dict(post, member)


def get_post(board_id: str, post_id: str) -> dict:
    """게시글 상세를 조회하고 조회수를 증가시킨다."""
    member = _current_member()
    board = _get_board_or_raise(board_id)
    _assert_board_readable(board, member)
    post = _get_post_or_raise(board_id, post_id)

    # PENDING 글은 작성자·승인자·관리자만 열람 가능
    if post.status == PostStatus.Pending:
        if post.author_id != member.id and not _is_admin() and not _is_approver(board_id, member.id):
            raise BoardException(ErrorStatus.BOARD_ACCESS_DENIED)

    # 첫 방문 시 조회수 증가, 재방문은 last_viewed_at 갱신만
    view = PostView.query.filter_by(post_id=post.id, member_id=member.id).first()
    try:
        if not view:
            db.session.add(PostView(post_id=post.id, member_id=member.id))
            post.view_count += 1
        else:
            view.last_viewed_at = datetime.now(timezone.utc)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

    return _post_detail_to_dict(post, member)


def update_post(board_id: str, post_id: str, data: dict) -> dict:
    """게시글을 수정한다. 작성자 또는 관리자만 가능."""
    member = _current_member()
    post = _get_post_or_raise(board_id, post_id)

    if post.author_id != member.id and not _is_admin():
        raise BoardException(ErrorStatus.POST_NOT_AUTHOR)

    if "title" in data:
        post.title = data["title"].strip()
    if "content" in data:
        post.content = data["content"]
    if "isPinned" in data and _is_admin():
        post.is_pinned = bool(data["isPinned"])

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    return _post_detail_to_dict(post, member)


def delete_post(board_id: str, post_id: str) -> None:
    """게시글을 소프트 삭제한다. 작성자 또는 관리자만 가능."""
    member = _current_member()
    post = _get_post_or_raise(board_id, post_id)

    if post.author_id != member.id and not _is_admin():
        raise BoardException(ErrorStatus.POST_NOT_AUTHOR)

    post.is_deleted = True
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e


# ── 게시글 승인/반려 ──────────────────────────────────────────

def approve_post(board_id: str, post_id: str) -> dict:
    """PENDING 상태 게시글을 PUBLISHED로 변경한다."""
    member = _current_member()
    post = _get_post_or_raise(board_id, post_id)

    if not _is_admin() and not _is_approver(board_id, member.id):
        raise BoardException(ErrorStatus.BOARD_APPROVAL_PERMISSION_DENIED)
    if post.status != PostStatus.Pending:
        raise BoardException(ErrorStatus.POST_ALREADY_PROCESSED)

    post.status = PostStatus.Published
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    return _post_to_dict(post)


def reject_post(board_id: str, post_id: str) -> dict:
    """PENDING 상태 게시글을 REJECTED로 변경한다."""
    member = _current_member()
    post = _get_post_or_raise(board_id, post_id)

    if not _is_admin() and not _is_approver(board_id, member.id):
        raise BoardException(ErrorStatus.BOARD_APPROVAL_PERMISSION_DENIED)
    if post.status != PostStatus.Pending:
        raise BoardException(ErrorStatus.POST_ALREADY_PROCESSED)

    post.status = PostStatus.Rejected
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    return _post_to_dict(post)


# ── 추천 (토글) ───────────────────────────────────────────────

def toggle_like(board_id: str, post_id: str) -> dict:
    """게시글 추천을 토글한다. 이미 추천했으면 취소, 아니면 추천."""
    member = _current_member()
    board = _get_board_or_raise(board_id)
    _assert_board_readable(board, member)
    post = _get_post_or_raise(board_id, post_id)

    existing = PostLike.query.filter_by(post_id=post.id, member_id=member.id).first()
    try:
        if existing:
            db.session.delete(existing)
            post.like_count = max(0, post.like_count - 1)
            liked = False
        else:
            db.session.add(PostLike(post_id=post.id, member_id=member.id))
            post.like_count += 1
            liked = True
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    return {"liked": liked, "likeCount": post.like_count}


# ── Comment CRUD ─────────────────────────────────────────────

def list_comments(board_id: str, post_id: str) -> list:
    """최상위 댓글과 대댓글을 계층 구조로 반환한다."""
    member = _current_member()
    board = _get_board_or_raise(board_id)
    _assert_board_readable(board, member)
    _get_post_or_raise(board_id, post_id)

    roots = (
        PostComment.query
        .filter_by(post_id=post_id, parent_id=None, is_deleted=False)
        .order_by(PostComment.created_at.asc())
        .all()
    )
    return [_comment_to_dict(c) for c in roots]


def create_comment(board_id: str, post_id: str, data: dict) -> dict:
    """댓글 또는 대댓글을 작성한다."""
    member = _current_member()
    board = _get_board_or_raise(board_id)
    _assert_board_readable(board, member)
    _get_post_or_raise(board_id, post_id)

    content = data.get("content", "").strip()
    if not content:
        raise ValueError("content는 필수입니다.")

    parent_id = data.get("parentId")
    if parent_id:
        parent = PostComment.query.filter_by(id=parent_id, post_id=post_id, is_deleted=False).first()
        if not parent:
            raise ValueError("parentId가 유효하지 않습니다.")

    comment = PostComment(
        post_id=post_id,
        parent_id=parent_id,
        author_id=member.id,
        content=content,
    )
    try:
        db.session.add(comment)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    return _comment_to_dict(comment)


def update_comment(board_id: str, post_id: str, comment_id: str, data: dict) -> dict:
    """댓글 내용을 수정한다. 작성자 또는 관리자만 가능."""
    member = _current_member()
    _get_post_or_raise(board_id, post_id)

    comment = PostComment.query.filter_by(id=comment_id, post_id=post_id, is_deleted=False).first()
    if not comment:
        raise BoardException(ErrorStatus.COMMENT_NOT_FOUND)
    if comment.author_id != member.id and not _is_admin():
        raise BoardException(ErrorStatus.COMMENT_NOT_AUTHOR)

    comment.content = data.get("content", "").strip()
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    return _comment_to_dict(comment)


def delete_comment(board_id: str, post_id: str, comment_id: str) -> None:
    """댓글을 소프트 삭제한다. 작성자 또는 관리자만 가능."""
    member = _current_member()
    _get_post_or_raise(board_id, post_id)

    comment = PostComment.query.filter_by(id=comment_id, post_id=post_id, is_deleted=False).first()
    if not comment:
        raise BoardException(ErrorStatus.COMMENT_NOT_FOUND)
    if comment.author_id != member.id and not _is_admin():
        raise BoardException(ErrorStatus.COMMENT_NOT_AUTHOR)

    comment.is_deleted = True
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e


# ── 게시판 승인자 관리 ────────────────────────────────────────

def list_approvers(board_id: str) -> list:
    """게시판 승인자 목록을 반환한다. 관리자만 조회 가능."""
    if not _is_admin():
        raise BoardException(ErrorStatus.BOARD_ACCESS_DENIED)
    _get_board_or_raise(board_id)
    approvers = BoardApprover.query.filter_by(board_id=board_id).all()
    # memberAccountId 포함: JS에서 account_id 기반 비교에 사용
    result = []
    for a in approvers:
        m = Member.query.get(a.member_id)
        result.append({
            "memberId":        a.member_id,
            "memberAccountId": m.account_id if m else None,
            "grantedBy":       a.granted_by,
            "grantedAt":       a.granted_at.isoformat(),
        })
    return result


def add_approver(board_id: str, member_id: str) -> dict:
    """게시판 승인자를 추가한다. 관리자만 호출 가능."""
    if not _is_admin():
        raise BoardException(ErrorStatus.BOARD_ACCESS_DENIED)
    _get_board_or_raise(board_id)

    if _is_approver(board_id, member_id):
        raise BoardException(ErrorStatus.BOARD_APPROVER_ALREADY_EXISTS)

    current = _current_member()
    approver = BoardApprover(board_id=board_id, member_id=member_id, granted_by=current.id)
    try:
        db.session.add(approver)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    return {"boardId": board_id, "memberId": member_id}


def remove_approver(board_id: str, member_id: str) -> None:
    """게시판 승인자를 제거한다. 관리자만 호출 가능."""
    if not _is_admin():
        raise BoardException(ErrorStatus.BOARD_ACCESS_DENIED)

    approver = BoardApprover.query.filter_by(board_id=board_id, member_id=member_id).first()
    if not approver:
        raise BoardException(ErrorStatus.BOARD_APPROVER_NOT_FOUND)
    try:
        db.session.delete(approver)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e


# ── 직렬화 헬퍼 ──────────────────────────────────────────────

# ── 첨부파일 (MinIO) ─────────────────────────────────────────

def upload_attachments(board_id: str, post_id: str, files: list) -> list:
    """multipart 파일 목록을 MinIO에 업로드하고 PostAttachment 레코드를 생성한다.
    files: Flask request.files.getlist('files') 결과 (FileStorage 리스트)
    파일 수 제한 없음 - 이미지 포함 모든 타입 허용."""
    member = _current_member()
    board = _get_board_or_raise(board_id)
    _assert_board_readable(board, member)
    post = _get_post_or_raise(board_id, post_id)

    if post.author_id != member.id and not _is_admin():
        raise BoardException(ErrorStatus.POST_NOT_AUTHOR)
    if not files:
        raise ValueError("업로드할 파일이 없습니다.")

    client = get_minio_client()
    created = []
    try:
        for file_storage in files:
            attachment_id = str(uuid.uuid4())
            original_name = file_storage.filename or "unnamed"
            mime_type = file_storage.content_type or "application/octet-stream"
            data = file_storage.read()
            size = len(data)

            # 오브젝트 키: {board_id}/{post_id}/{attachment_id}/{원본파일명}
            object_name = f"{board_id}/{post_id}/{attachment_id}/{original_name}"
            client.put_object(
                bucket_name=BOARD_BUCKET,
                object_name=object_name,
                data=io.BytesIO(data),
                length=size,
                content_type=mime_type,
            )
            attachment = PostAttachment(
                id=attachment_id,
                post_id=post_id,
                original_name=original_name,
                s3_key=object_name,
                file_size=size,
                content_type=mime_type,
            )
            db.session.add(attachment)
            created.append(attachment)
        db.session.commit()
    except S3Error as e:
        db.session.rollback()
        raise BoardException(ErrorStatus.ATTACHMENT_UPLOAD_FAILED) from e
    except Exception as e:
        db.session.rollback()
        raise e

    return [_attachment_to_dict(a) for a in created]


def list_attachments(board_id: str, post_id: str) -> list:
    """게시글의 첨부파일 목록을 반환한다."""
    member = _current_member()
    board = _get_board_or_raise(board_id)
    _assert_board_readable(board, member)
    _get_post_or_raise(board_id, post_id)

    attachments = PostAttachment.query.filter_by(post_id=post_id).all()
    return [_attachment_to_dict(a) for a in attachments]


def get_attachment_url(board_id: str, post_id: str, attachment_id: str, expires: int = 3600) -> str:
    """첨부파일의 presigned 다운로드 URL을 반환한다. 기본 유효시간 1시간."""
    member = _current_member()
    board = _get_board_or_raise(board_id)
    _assert_board_readable(board, member)
    _get_post_or_raise(board_id, post_id)

    attachment = PostAttachment.query.filter_by(id=attachment_id, post_id=post_id).first()
    if not attachment:
        raise BoardException(ErrorStatus.ATTACHMENT_NOT_FOUND)

    client = get_minio_client()
    try:
        url = client.presigned_get_object(
            bucket_name=BOARD_BUCKET,
            object_name=attachment.s3_key,
            expires=timedelta(seconds=expires),
        )
    except S3Error as e:
        raise BoardException(ErrorStatus.ATTACHMENT_NOT_FOUND) from e
    return url


def stream_attachment(board_id: str, post_id: str, attachment_id: str) -> tuple:
    """첨부파일 원본 바이너리를 스트리밍한다.
    반환: (data: bytes, content_type: str, filename: str)
    <img src="/inline"> 태그나 fetch → blob URL 방식 모두 지원."""
    member = _current_member()
    board = _get_board_or_raise(board_id)
    _assert_board_readable(board, member)
    _get_post_or_raise(board_id, post_id)

    attachment = PostAttachment.query.filter_by(id=attachment_id, post_id=post_id).first()
    if not attachment:
        raise BoardException(ErrorStatus.ATTACHMENT_NOT_FOUND)

    client = get_minio_client()
    try:
        response = client.get_object(BOARD_BUCKET, attachment.s3_key)
        data = response.read()
        response.close()
        response.release_conn()
    except S3Error as e:
        raise BoardException(ErrorStatus.ATTACHMENT_NOT_FOUND) from e

    return data, attachment.content_type or "application/octet-stream", attachment.original_name


def render_post_content(board_id: str, post_id: str) -> str:
    """본문 내 {{ATTACHMENT:id}} 플레이스홀더를 presigned URL로 치환한 HTML을 반환한다.
    리치에디터가 이미지 삽입 시 {{ATTACHMENT:uuid}} 형식으로 저장했을 때 사용."""
    import re
    member = _current_member()
    board = _get_board_or_raise(board_id)
    _assert_board_readable(board, member)
    post = _get_post_or_raise(board_id, post_id)

    content = post.content
    pattern = re.compile(r'\{\{ATTACHMENT:([0-9a-f\-]{36})\}\}')
    ids_needed = set(pattern.findall(content))
    if not ids_needed:
        return content

    # 필요한 첨부파일만 일괄 조회
    attachments = PostAttachment.query.filter(
        PostAttachment.post_id == post_id,
        PostAttachment.id.in_(ids_needed),
    ).all()

    client = get_minio_client()
    url_map: dict[str, str] = {}
    for a in attachments:
        try:
            url_map[a.id] = client.presigned_get_object(
                bucket_name=BOARD_BUCKET,
                object_name=a.s3_key,
                expires=timedelta(hours=6),
            )
        except S3Error:
            url_map[a.id] = ""

    def replace(m: re.Match) -> str:
        return url_map.get(m.group(1), "")

    return pattern.sub(replace, content)


def delete_attachment(board_id: str, post_id: str, attachment_id: str) -> None:
    """첨부파일을 MinIO와 DB에서 삭제한다. 작성자 또는 관리자만 가능."""
    member = _current_member()
    post = _get_post_or_raise(board_id, post_id)

    if post.author_id != member.id and not _is_admin():
        raise BoardException(ErrorStatus.POST_NOT_AUTHOR)

    attachment = PostAttachment.query.filter_by(id=attachment_id, post_id=post_id).first()
    if not attachment:
        raise BoardException(ErrorStatus.ATTACHMENT_NOT_FOUND)

    client = get_minio_client()
    try:
        client.remove_object(BOARD_BUCKET, attachment.s3_key)
    except S3Error:
        pass  # MinIO에 없어도 DB 레코드는 삭제 진행
    try:
        db.session.delete(attachment)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e


def _board_to_dict(b: Board) -> dict:
    """Board 모델을 응답 dict로 변환한다."""
    return {
        "boardId":           b.id,
        "boardName":         b.board_name,
        "boardType":         b.board_type.value,
        "description":       b.description,
        "departmentId":      b.department_id,
        "isActive":          b.is_active,
        "isPublic":          b.is_public,
        "requiresApproval":  b.requires_approval,
        "approvalExpiresAt": b.approval_expires_at.isoformat() if b.approval_expires_at else None,
        "approvalPurpose":   b.approval_purpose,
        "createdBy":         b.created_by,
        "createdAt":         b.created_at.isoformat(),
    }


def _post_to_dict(p: Post, author: Member = None) -> dict:
    """Post 모델을 목록용 dict로 변환한다 (content 제외). author 미전달 시 DB 조회."""
    if author is None:
        author = Member.query.get(p.author_id)
    return {
        "postId":          p.id,
        "boardId":         p.board_id,
        "title":           p.title,
        "authorId":        p.author_id,
        "authorName":      author.name_ko if author else None,
        "authorAccountId": author.account_id if author else None,
        "status":          p.status.value,
        "viewCount":       p.view_count,
        "likeCount":       p.like_count,
        "isPinned":        p.is_pinned,
        "createdAt":       p.created_at.isoformat(),
        "updatedAt":       p.updated_at.isoformat(),
    }


def _post_detail_to_dict(p: Post, member: Member = None) -> dict:
    """Post 모델을 상세용 dict로 변환한다 (content + isLiked + boardName 포함)."""
    d = _post_to_dict(p)
    d["content"] = p.content
    # 게시판 이름 추가
    board = Board.query.get(p.board_id)
    d["boardName"] = board.board_name if board else None
    # 좋아요 여부 추가
    if member:
        d["isLiked"] = PostLike.query.filter_by(post_id=p.id, member_id=member.id).first() is not None
    else:
        d["isLiked"] = False
    attachments = PostAttachment.query.filter_by(post_id=p.id).all()
    d["attachments"] = [_attachment_to_dict(a) for a in attachments]
    return d


def _attachment_to_dict(a: PostAttachment) -> dict:
    """PostAttachment 모델을 응답 dict로 변환한다."""
    return {
        "attachmentId": a.id,
        "postId":       a.post_id,
        "originalName": a.original_name,
        "fileSize":     a.file_size,
        "contentType":  a.content_type,
        "createdAt":    a.created_at.isoformat(),
    }


def _comment_to_dict(c: PostComment) -> dict:
    """댓글을 대댓글 포함 dict로 변환한다 (1단계 중첩). 작성자 이름·accountId 포함."""
    author = Member.query.get(c.author_id)
    replies = (
        PostComment.query
        .filter_by(parent_id=c.id)
        .order_by(PostComment.created_at.asc())
        .all()
    )
    return {
        "commentId":        c.id,
        "postId":           c.post_id,
        "parentId":         c.parent_id,
        "authorId":         c.author_id,
        "authorName":       author.name_ko if author else None,
        "authorAccountId":  author.account_id if author else None,
        "content":          c.content,
        "isDeleted":        c.is_deleted,
        "createdAt":        c.created_at.isoformat(),
        "updatedAt":        c.updated_at.isoformat(),
        "replies":   [
            {
                "commentId":        r.id,
                "postId":           r.post_id,
                "parentId":         r.parent_id,
                "authorId":         r.author_id,
                "authorName":       (lambda m: m.name_ko if m else None)(Member.query.get(r.author_id)),
                "authorAccountId":  (lambda m: m.account_id if m else None)(Member.query.get(r.author_id)),
                "content":          r.content,
                "isDeleted":        r.is_deleted,
                "createdAt":        r.created_at.isoformat(),
                "updatedAt":        r.updated_at.isoformat(),
            }
            for r in replies
        ],
    }
