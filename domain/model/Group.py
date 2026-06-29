import uuid

from domain.model.BaseEntity import BaseEntity
from extensions import db

# ── Association table (Group ↔ Member) ───────────────────────
tb_group_member = db.Table(
    'tb_group_member',
    db.Column(
        'group_id',
        db.String(36),
        db.ForeignKey('tb_group.group_id', ondelete='CASCADE'),
        primary_key=True,
    ),
    db.Column(
        'member_id',
        db.String(36),
        db.ForeignKey('tb_members.member_id', ondelete='CASCADE'),
        primary_key=True,
    ),
)


class Group(BaseEntity):
    __tablename__ = 'tb_group'

    id = db.Column('group_id', db.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    group_name  = db.Column(db.String(50),  unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    members = db.relationship(
        'Member',
        secondary=tb_group_member,
        lazy='select',
        backref=db.backref('groups', lazy='select'),
    )

    def __repr__(self) -> str:
        return f"<Group id={self.id} name={self.group_name}>"
