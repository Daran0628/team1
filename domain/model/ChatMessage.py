import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME as MySQLDATETIME

from domain.enum.ChatMessageType import ChatMessageType
from extensions import db


class ChatMessage(db.Model):
    __tablename__ = "tb_chat_message"
    __table_args__ = (
        sa.Index("idx_chat_message_room_time", "room_id", "created_at"),
        sa.Index("ft_chat_message_content", "content", mysql_prefix="FULLTEXT"),
    )

    id = db.Column("message_id", db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    room_id   = db.Column(db.String(36), db.ForeignKey("tb_chat_room.room_id",   ondelete="CASCADE"), nullable=False)
    sender_id = db.Column(db.String(36), db.ForeignKey("tb_members.member_id",   ondelete="CASCADE"), nullable=False)

    message_type = db.Column(
        sa.Enum(ChatMessageType, values_callable=lambda e: [i.value for i in e]),
        nullable=False,
        default=ChatMessageType.Text,
    )
    content    = db.Column(db.Text,    nullable=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)

    # 마이크로초(fsp=6) → 동시 메시지 정렬 정확도 보장
    created_at = db.Column(
        MySQLDATETIME(fsp=6),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    room   = db.relationship("ChatRoom",  back_populates="messages")
    sender = db.relationship("Member",    backref=db.backref("chat_messages", lazy="select"))
    files  = db.relationship("ChatFile",  back_populates="message", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} room={self.room_id} type={self.message_type}>"
