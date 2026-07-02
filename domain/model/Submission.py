import uuid
from datetime import datetime, timezone

import sqlalchemy as sa

from extensions import db


class Submission(db.Model):
    __tablename__ = "tb_submission"

    submission_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    problem_id    = db.Column(db.String(36), db.ForeignKey('tb_problem.problem_id', ondelete='CASCADE'),
                              nullable=False)
    member_id     = db.Column(db.String(36), nullable=False)  # 제출자

    language    = db.Column(db.String(20), nullable=False)   # PYTHON / CPP / JAVA ...
    source_path = db.Column(db.String(255), nullable=False)  # MinIO 오브젝트 키

    status = db.Column(
        sa.Enum(
            'PENDING', 'JUDGING', 'ACCEPTED', 'WRONG_ANSWER',
            'TIME_LIMIT_EXCEEDED', 'RUNTIME_ERROR', 'COMPILE_ERROR',
            name='submission_status',
        ),
        nullable=False,
        default='PENDING',
    )

    score      = db.Column(db.Integer, nullable=False, default=0)
    runtime_ms = db.Column(db.Integer, nullable=True)
    memory_kb  = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    problem = db.relationship('Problem', back_populates='submissions')

    def __repr__(self) -> str:
        return f"<Submission id={self.submission_id} problem={self.problem_id} status={self.status}>"
