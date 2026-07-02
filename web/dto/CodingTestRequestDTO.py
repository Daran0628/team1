from dataclasses import dataclass, field
from typing import List

DIFFICULTY_LEVELS = ('BEGINNER', 'BASIC', 'INTERMEDIATE', 'ADVANCED')


@dataclass
class TestCaseInputDTO:
    input:           str
    expected_output: str
    is_sample:       bool = False


@dataclass
class CreateProblemRequestDTO:
    title:           str
    description:     str
    difficulty:      str = 'BEGINNER'
    time_limit_ms:   int = 2000
    memory_limit_mb: int = 256
    test_cases:      List[TestCaseInputDTO] = field(default_factory=list)

    def __post_init__(self):
        if not self.title or not self.title.strip():
            raise ValueError("title은 필수입니다.")
        if not self.description or not self.description.strip():
            raise ValueError("description은 필수입니다.")
        if not self.test_cases:
            raise ValueError("테스트케이스가 최소 1개 필요합니다.")
        if self.difficulty not in DIFFICULTY_LEVELS:
            raise ValueError(f"difficulty는 {', '.join(DIFFICULTY_LEVELS)} 중 하나여야 합니다.")


@dataclass
class CreateSubmissionRequestDTO:
    problem_id:  str
    language:    str
    source_code: str

    def __post_init__(self):
        if not self.problem_id:
            raise ValueError("problemId는 필수입니다.")
        if not self.language or not self.language.strip():
            raise ValueError("language는 필수입니다.")
        if not self.source_code or not self.source_code.strip():
            raise ValueError("제출할 코드가 비어있습니다.")
