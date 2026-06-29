from dataclasses import dataclass
from datetime import datetime

from domain.enum.AccountType import AccountType
from domain.enum.EnrollmentStatus import EnrollmentStatus


@dataclass
class LoginResponseDTO:
    access_token: str           # JSON body 반환
    name_ko: str
    employee_no: str
    dept_path_name: str
    account_id: str
    enrollment_status: EnrollmentStatus
    account_type: AccountType


@dataclass
class LogoutResponseDTO:
    logout_at: datetime


@dataclass
class RefreshResponseDTO:
    access_token: str           # JSON body 반환
