from dataclasses import dataclass
from datetime import datetime


@dataclass
class MemberInfoResponseDTO:
    account_id: str
    name_ko: str
    employee_no: str

    department_name: str

    email: str
    address: str
    car_num: str | None

    account_type: str
    work_type: str

    last_login: datetime | None


@dataclass
class MemberSearchResultDTO:
    name_ko: str
    department_name: str
    department_phone: str | None
    email: str


@dataclass
class DepartmentOptionDTO:
    department_id: str
    department_name: str