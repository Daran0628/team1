import uuid
from datetime import datetime, timezone

import sqlalchemy as sa

from domain.enum.ChatRoomType import ChatRoomType
from domain.enum.ChatRoomRole import ChatRoomRole
from domain.model.BaseEntity import BaseEntity
from extensions import db


class ChatRoom(BaseEntity):
    __tablename__ = "tb_chat_room"

    id = db.Column("room_id", db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    room_type = db.Column(
        sa.Enum(ChatRoomType, values_callable=lambda e: [i.value for i in e]),
        nullable=False,
    )
    room_name  = db.Column(db.String(100), nullable=True)
    direct_key = db.Column(db.String(73),  unique=True, nullable=True)
    created_by = db.Column(db.String(36),  nullable=False)  # member_id (FK 없음)

    members  = db.relationship("ChatRoomMember", back_populates="room", cascade="all, delete-orphan")
    messages = db.relationship("ChatMessage",     back_populates="room", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ChatRoom id={self.id} type={self.room_type}>"


class ChatRoomMember(db.Model):
    __tablename__ = "tb_chat_room_member"

    room_id   = db.Column(db.String(36), db.ForeignKey("tb_chat_room.room_id",   ondelete="CASCADE"), primary_key=True)
    member_id = db.Column(db.String(36), db.ForeignKey("tb_members.member_id",   ondelete="CASCADE"), primary_key=True)

    room_role = db.Column(
        sa.Enum(ChatRoomRole, values_callable=lambda e: [i.value for i in e]),
        nullable=False,
        default=ChatRoomRole.Member,
    )
    last_read_at = db.Column(db.DateTime, nullable=True)
    joined_at    = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    is_active    = db.Column(db.Boolean,  nullable=False, default=True)

    room   = db.relationship("ChatRoom",  back_populates="members")
    member = db.relationship("Member",    backref=db.backref("chat_memberships", lazy="select"))

    def __repr__(self) -> str:
        return f"<ChatRoomMember room={self.room_id} member={self.member_id} role={self.room_role}>"
