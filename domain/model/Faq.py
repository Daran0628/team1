import uuid

from domain.model.BaseEntity import BaseEntity
from extensions import db


class Faq(BaseEntity):
    __tablename__ = "tb_faq"

    id = db.Column(
        "faq_id",
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    member_id = db.Column(
        db.String(36),
        db.ForeignKey("tb_members.member_id"),
        nullable=False
    )

    question = db.Column(db.String(200), nullable=False)
    answer   = db.Column(db.Text,        nullable=False)
    category = db.Column(db.String(50),  nullable=True)

    author = db.relationship("Member", backref="faqs", lazy=True)

    def __repr__(self):
        return f"<Faq id={self.id} question={self.question}>"