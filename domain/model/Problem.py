import uuid
from datetime import datetime, timezone

from extensions import db


class Problem(db.Model):
    __tablename__ = "tb_problem"

    problem_id  = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)

    time_limit_ms   = db.Column(db.Integer, nullable=False, default=2000)
    memory_limit_mb = db.Column(db.Integer, nullable=False, default=256)

    created_by = db.Column(db.String(36), nullable=False)  # member_id

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    test_cases  = db.relationship('TestCase', back_populates='problem',
                                  cascade='all, delete-orphan', lazy='select')
    submissions = db.relationship('Submission', back_populates='problem',
                                  cascade='all, delete-orphan', lazy='select')

    def __repr__(self) -> str:
        return f"<Problem id={self.problem_id} title={self.title}>"
