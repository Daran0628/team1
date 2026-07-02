from datetime import datetime, timezone

from extensions import db


class Score(db.Model):
    __tablename__ = "tb_score"

    member_id  = db.Column(db.String(36), primary_key=True)
    problem_id = db.Column(db.String(36), db.ForeignKey('tb_problem.problem_id', ondelete='CASCADE'),
                           primary_key=True)

    best_score = db.Column(db.Integer, nullable=False, default=0)
    updated_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Score member={self.member_id} problem={self.problem_id} best={self.best_score}>"
