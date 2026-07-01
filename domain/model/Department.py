import uuid

from extensions import db


class Department(db.Model):
    __tablename__ = "tb_department"

    id = db.Column(
        "department_id",
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    department_name = db.Column(
        db.String(50),
        nullable=False,
        unique=True
    )

 # Member와 양방향 관계 (선택사항)
    members = db.relationship(
        "Member",
        backref="department",
        lazy="joined"
    )

    def __repr__(self) -> str:
        return f"<Department id={self.id} name={self.department_name}>"