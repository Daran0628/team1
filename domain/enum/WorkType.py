from enum import Enum


class WorkType(Enum):
    FULL_TIME = "FULL_TIME"   # 정규직
    PART_TIME = "PART_TIME"   # 파트타임
    CONTRACT = "CONTRACT"     # 계약직
    INTERN = "INTERN"         # 인턴
