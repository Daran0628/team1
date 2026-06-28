from enum import Enum


class EnrollmentStatus(Enum):
    ACTIVE = "ACTIVE"       # 재직
    ON_LEAVE = "ON_LEAVE"   # 휴직
    RESIGNED = "RESIGNED"   # 퇴직
