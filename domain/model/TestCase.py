import uuid
from datetime import datetime, timezone

from extensions import db


class TestCase(db.Model):
    __tablename__ = "tb_test_case"

    test_case_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    problem_id   = db.Column(db.String(36), db.ForeignKey('tb_problem.problem_id', ondelete='CASCADE'),
                             nullable=False)

    input            = db.Column(db.Text, nullable=False)
    expected_output  = db.Column(db.Text, nullable=False)
    is_sample        = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    problem = db.relationship('Problem', back_populates='test_cases')

    def __repr__(self) -> str:
        return f"<TestCase id={self.test_case_id} problem={self.problem_id} sample={self.is_sample}>"
