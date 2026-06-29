import uuid
import sqlalchemy as sa

from domain.model.BaseEntity import BaseEntity
from extensions import db


class TicketStatus(str):
    OPEN        = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED    = "RESOLVED"
    CLOSED      = "CLOSED"


class Ticket(BaseEntity):
    __tablename__ = "tb_ticket"

    id = db.Column(
        "ticket_id",
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    member_id = db.Column(
        db.String(36),
        db.ForeignKey("tb_members.member_id"),
        nullable=False
    )

    assigned_to = db.Column(
        db.String(36),
        db.ForeignKey("tb_members.member_id"),
        nullable=True
    )

    title    = db.Column(db.String(100), nullable=False)
    content  = db.Column(db.Text,        nullable=False)
    status   = db.Column(db.String(20),  nullable=False, default="OPEN")
    priority = db.Column(db.String(20),  nullable=False, default="MEDIUM")

    requester = db.relationship("Member", foreign_keys=[member_id],  backref="tickets",          lazy=True)
    assignee  = db.relationship("Member", foreign_keys=[assigned_to], backref="assigned_tickets", lazy=True)

    def __repr__(self):
        return f"<Ticket id={self.id} title={self.title} status={self.status}>"