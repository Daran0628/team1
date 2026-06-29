import sqlalchemy as sa

from domain.enum.AccountType import AccountType
from domain.enum.EnrollmentStatus import EnrollmentStatus
from domain.enum.WorkType import WorkType
from domain.model.BaseEntity import BaseEntity
from extensions import db


class Member(BaseEntity):
    __tablename__ = "tb_members"

    id = db.Column("member_id", db.BigInteger, primary_key=True, autoincrement=True)

    name_ko = db.Column(db.String(18), nullable=False)
    account_id = db.Column(db.String(20), nullable=False)
    employee_no = db.Column(db.String(10), nullable=False)
    dept_path_name = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(60), nullable=False)

    enrollment_status = db.Column(
        sa.Enum(EnrollmentStatus, values_callable=lambda e: [i.value for i in e]),
        nullable=False,
    )
    account_type = db.Column(
        sa.Enum(AccountType, values_callable=lambda e: [i.value for i in e]),
        nullable=False,
    )
    work_type = db.Column(
        sa.Enum(WorkType, values_callable=lambda e: [i.value for i in e]),
        nullable=False,
    )

    car_num = db.Column(db.String(8), nullable=True)
    address = db.Column(db.String(50), nullable=False)
    deleted_at = db.Column(db.Date, nullable=True)

    # ── UserDetails 동등 인터페이스 ──────────────────────────────

    def get_authorities(self) -> list[str]:
        return [self.account_type.name]

    def get_username(self) -> str:
        return self.account_id

    @property
    def is_account_non_expired(self) -> bool:
        return True

    @property
    def is_account_non_locked(self) -> bool:
        return True

    @property
    def is_credentials_non_expired(self) -> bool:
        return True

    @property
    def is_enabled(self) -> bool:
        return self.enrollment_status == EnrollmentStatus.ACTIVE

    def __repr__(self) -> str:
        return f"<Member id={self.id} account_id={self.account_id}>"
