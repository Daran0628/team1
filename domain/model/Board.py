import uuid
from datetime import datetime, timezone

import sqlalchemy as sa

from domain.enum.BoardType import BoardType
from domain.enum.PostStatus import PostStatus
from domain.model.BaseEntity import BaseEntity
from extensions import db


class Board(BaseEntity):
    __tablename__ = "tb_board"

    id = db.Column("board_id", db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    board_name  = db.Column(db.String(100), nullable=False)
    board_type  = db.Column(
        sa.Enum(BoardType, values_callable=lambda e: [i.value for i in e]),
        nullable=False,
        default=BoardType.Free,
    )
    description     = db.Column(db.String(500), nullable=True)
    department_id   = db.Column(
        db.String(36),
        db.ForeignKey("tb_department.department_id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active           = db.Column(db.Boolean,  nullable=False, default=True)
    is_public           = db.Column(db.Boolean,  nullable=False, default=True)   # False = 부서원만
    requires_approval   = db.Column(db.Boolean,  nullable=False, default=False)
    approval_expires_at = db.Column(db.DateTime, nullable=True)
    approval_purpose    = db.Column(db.String(200), nullable=True)
    created_by          = db.Column(db.String(36),  nullable=False)              # member_id (FK 없음)

    posts     = db.relationship("Post",          back_populates="board", cascade="all, delete-orphan")
    approvers = db.relationship("BoardApprover", back_populates="board", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Board id={self.id} name={self.board_name} type={self.board_type}>"


class Post(BaseEntity):
    __tablename__ = "tb_post"

    id = db.Column("post_id", db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    board_id  = db.Column(db.String(36), db.ForeignKey("tb_board.board_id", ondelete="CASCADE"), nullable=False)
    title     = db.Column(db.String(300), nullable=False)
    content   = db.Column(db.Text,        nullable=False)
    author_id = db.Column(db.String(36),  nullable=False)                        # member_id (FK 없음)
    status    = db.Column(
        sa.Enum(PostStatus, values_callable=lambda e: [i.value for i in e]),
        nullable=False,
        default=PostStatus.Published,
    )
    view_count = db.Column(db.Integer, nullable=False, default=0)
    like_count = db.Column(db.Integer, nullable=False, default=0)
    is_pinned  = db.Column(db.Boolean, nullable=False, default=False)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)

    board       = db.relationship("Board",           back_populates="posts")
    attachments = db.relationship("PostAttachment",  back_populates="post", cascade="all, delete-orphan")
    comments    = db.relationship("PostComment",     back_populates="post", cascade="all, delete-orphan",
                                  primaryjoin="and_(PostComment.post_id == Post.id, PostComment.parent_id == None)")
    likes       = db.relationship("PostLike",        back_populates="post", cascade="all, delete-orphan")
    views       = db.relationship("PostView",        back_populates="post", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Post id={self.id} title={self.title[:20]} status={self.status}>"


class PostAttachment(db.Model):
    __tablename__ = "tb_post_attachment"

    id = db.Column("attachment_id", db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    post_id       = db.Column(db.String(36),  db.ForeignKey("tb_post.post_id", ondelete="CASCADE"), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    s3_key        = db.Column(db.String(500), nullable=False)
    file_size     = db.Column(db.BigInteger,  nullable=False, default=0)
    content_type  = db.Column(db.String(100), nullable=True)
    created_at    = db.Column(db.DateTime,    nullable=False, default=lambda: datetime.now(timezone.utc))

    post = db.relationship("Post", back_populates="attachments")

    def __repr__(self) -> str:
        return f"<PostAttachment id={self.id} name={self.original_name}>"


class PostComment(BaseEntity):
    __tablename__ = "tb_post_comment"

    id = db.Column("comment_id", db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    post_id   = db.Column(db.String(36), db.ForeignKey("tb_post.post_id",         ondelete="CASCADE"), nullable=False)
    parent_id = db.Column(db.String(36), db.ForeignKey("tb_post_comment.comment_id", ondelete="CASCADE"), nullable=True)
    author_id = db.Column(db.String(36), nullable=False)                          # member_id (FK 없음)
    content   = db.Column(db.Text,    nullable=False)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)

    post    = db.relationship("Post",        back_populates="comments",
                              primaryjoin="and_(PostComment.post_id == Post.id, PostComment.parent_id == None)")
    replies = db.relationship("PostComment", backref=db.backref("parent", remote_side="PostComment.id"),
                              cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<PostComment id={self.id} post={self.post_id}>"


class PostLike(db.Model):
    __tablename__ = "tb_post_like"

    post_id   = db.Column(db.String(36), db.ForeignKey("tb_post.post_id", ondelete="CASCADE"), primary_key=True)
    member_id = db.Column(db.String(36), primary_key=True)
    created_at = db.Column(db.DateTime,  nullable=False, default=lambda: datetime.now(timezone.utc))

    post = db.relationship("Post", back_populates="likes")

    def __repr__(self) -> str:
        return f"<PostLike post={self.post_id} member={self.member_id}>"


class PostView(db.Model):
    __tablename__ = "tb_post_view"

    post_id    = db.Column(db.String(36), db.ForeignKey("tb_post.post_id", ondelete="CASCADE"), primary_key=True)
    member_id  = db.Column(db.String(36), primary_key=True)
    last_viewed_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    post = db.relationship("Post", back_populates="views")

    def __repr__(self) -> str:
        return f"<PostView post={self.post_id} member={self.member_id}>"


class BoardApprover(db.Model):
    __tablename__ = "tb_board_approver"

    board_id  = db.Column(db.String(36), db.ForeignKey("tb_board.board_id",   ondelete="CASCADE"), primary_key=True)
    member_id = db.Column(db.String(36), db.ForeignKey("tb_members.member_id", ondelete="CASCADE"), primary_key=True)
    granted_by = db.Column(db.String(36), nullable=False)                        # member_id (FK 없음)
    granted_at = db.Column(db.DateTime,   nullable=False, default=lambda: datetime.now(timezone.utc))

    board  = db.relationship("Board",  back_populates="approvers")
    member = db.relationship("Member", backref=db.backref("board_approvals", lazy="select"))

    def __repr__(self) -> str:
        return f"<BoardApprover board={self.board_id} member={self.member_id}>"
