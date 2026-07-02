from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ProblemSummaryDTO:
    problem_id:      str
    title:           str
    time_limit_ms:   int
    memory_limit_mb: int
    created_by:      str
    created_at:      datetime


@dataclass
class TestCaseDTO:
    test_case_id:     str
    input:            str
    expected_output:  str
    is_sample:        bool


@dataclass
class ProblemDetailDTO:
    problem_id:      str
    title:           str
    description:     str
    time_limit_ms:   int
    memory_limit_mb: int
    created_by:      str
    created_at:      datetime
    sample_test_cases: List[TestCaseDTO] = field(default_factory=list)


@dataclass
class SubmissionResponseDTO:
    submission_id: str
    problem_id:    str
    member_id:     str
    language:      str
    status:        str
    score:         int
    runtime_ms:    Optional[int]
    memory_kb:     Optional[int]
    created_at:    datetime
    updated_at:    datetime
