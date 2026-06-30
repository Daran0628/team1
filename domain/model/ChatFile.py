import uuid
from datetime import datetime, timezone

from extensions import db


class ChatFile(db.Model):
    __tablename__ = "tb_chat_file"

    id = db.Column("file_id", db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    message_id    = db.Column(db.String(36),  db.ForeignKey("tb_chat_message.message_id", ondelete="CASCADE"), nullable=False)
    resource_id   = db.Column(db.String(36),  nullable=False)  # tb_storage_resource.resource_id (FK 없음)
    original_name = db.Column(db.String(255), nullable=False)
    file_size     = db.Column(db.BigInteger,  nullable=False)
    mime_type     = db.Column(db.String(100), nullable=False)
    created_at    = db.Column(db.DateTime,    nullable=False, default=lambda: datetime.now(timezone.utc))

    message = db.relationship("ChatMessage", back_populates="files")

    def __repr__(self) -> str:
        return f"<ChatFile id={self.id} name={self.original_name}>"
