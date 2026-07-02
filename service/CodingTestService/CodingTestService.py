import io
import logging
import uuid

from minio import S3Error

from core.config.MinioConfig import get_minio_client
from core.response.ErrorStatus import ErrorStatus
from domain.model.Problem import Problem
from domain.model.TestCase import TestCase
from domain.model.Submission import Submission
from domain.model.StorageBucket import StorageBucket
from extensions import db
from web.dto.CodingTestRequestDTO import CreateProblemRequestDTO, CreateSubmissionRequestDTO
from web.dto.CodingTestResponseDTO import (
    ProblemSummaryDTO,
    ProblemDetailDTO,
    TestCaseDTO,
    SubmissionResponseDTO,
)

logger = logging.getLogger(__name__)

SUBMISSION_BUCKET = "coding-test-submissions"

LANGUAGE_EXTENSIONS = {
    "PYTHON": ".py",
    "CPP": ".cpp",
    "JAVA": ".java",
}


class CodingTestException(Exception):
    def __init__(self, error_status: ErrorStatus, detail: str | None = None):
        self.error_status = error_status
        self.detail = detail
        super().__init__(detail or error_status.message)


def _minio():
    return get_minio_client()


def ensure_submission_bucket() -> None:
    client = _minio()
    if StorageBucket.query.filter_by(bucket_name=SUBMISSION_BUCKET).first():
        return
    try:
        if not client.bucket_exists(SUBMISSION_BUCKET):
            client.make_bucket(SUBMISSION_BUCKET)
    except S3Error as e:
        logger.error("%s 버킷 생성 실패: %s", SUBMISSION_BUCKET, e)
        return
    db.session.add(StorageBucket(bucket_name=SUBMISSION_BUCKET, created_by="system"))
    db.session.commit()
    logger.info("%s 버킷 생성 완료", SUBMISSION_BUCKET)


# ── 문제 ─────────────────────────────────────────────────────────

def create_problem(dto: CreateProblemRequestDTO, created_by: str) -> ProblemDetailDTO:
    problem = Problem(
        title=dto.title.strip(),
        description=dto.description.strip(),
        time_limit_ms=dto.time_limit_ms,
        memory_limit_mb=dto.memory_limit_mb,
        created_by=created_by,
    )
    db.session.add(problem)
    db.session.flush()  # problem_id 확보 (test_case FK에 필요)

    for tc in dto.test_cases:
        db.session.add(TestCase(
            problem_id=problem.problem_id,
            input=tc.input,
            expected_output=tc.expected_output,
            is_sample=tc.is_sample,
        ))

    db.session.commit()
    return _problem_to_detail_dto(problem)


def list_problems() -> list[ProblemSummaryDTO]:
    problems = Problem.query.order_by(Problem.created_at.desc()).all()
    return [_problem_to_summary_dto(p) for p in problems]


def get_problem(problem_id: str) -> ProblemDetailDTO:
    problem = _get_problem_or_raise(problem_id)
    return _problem_to_detail_dto(problem)


# ── 제출 ─────────────────────────────────────────────────────────

def create_submission(dto: CreateSubmissionRequestDTO, member_id: str) -> SubmissionResponseDTO:
    problem = _get_problem_or_raise(dto.problem_id)

    language = dto.language.strip().upper()
    if language not in LANGUAGE_EXTENSIONS:
        raise CodingTestException(
            ErrorStatus.CODE_UNSUPPORTED_LANGUAGE,
            f"지원하지 않는 언어입니다: {language} (지원: {', '.join(LANGUAGE_EXTENSIONS)})",
        )

    ensure_submission_bucket()

    submission_id = str(uuid.uuid4())
    object_name = f"{problem.problem_id}/{member_id}/{submission_id}{LANGUAGE_EXTENSIONS[language]}"

    data = dto.source_code.encode("utf-8")
    try:
        _minio().put_object(
            bucket_name=SUBMISSION_BUCKET,
            object_name=object_name,
            data=io.BytesIO(data),
            length=len(data),
            content_type="text/plain",
        )
    except S3Error as e:
        raise CodingTestException(ErrorStatus.CODE_SUBMISSION_UPLOAD_FAILED) from e

    submission = Submission(
        submission_id=submission_id,
        problem_id=problem.problem_id,
        member_id=member_id,
        language=language,
        source_path=object_name,
        status="PENDING",
    )
    db.session.add(submission)
    db.session.commit()

    # TODO(다음 단계): 비동기 채점 큐(Redis+RQ)에 submission_id enqueue

    return _submission_to_dto(submission)


def get_submission(submission_id: str, requester_id: str, is_admin: bool = False) -> SubmissionResponseDTO:
    submission = Submission.query.get(submission_id)
    if not submission:
        raise CodingTestException(ErrorStatus.CODE_SUBMISSION_NOT_FOUND)
    if not is_admin and submission.member_id != requester_id:
        raise CodingTestException(ErrorStatus._FORBIDDEN)
    return _submission_to_dto(submission)


def list_my_submissions(member_id: str, problem_id: str | None = None) -> list[SubmissionResponseDTO]:
    query = Submission.query.filter_by(member_id=member_id)
    if problem_id:
        query = query.filter_by(problem_id=problem_id)
    submissions = query.order_by(Submission.created_at.desc()).all()
    return [_submission_to_dto(s) for s in submissions]


# ── 내부 헬퍼 ─────────────────────────────────────────────────────

def _get_problem_or_raise(problem_id: str) -> Problem:
    problem = Problem.query.get(problem_id)
    if not problem:
        raise CodingTestException(ErrorStatus.CODE_PROBLEM_NOT_FOUND)
    return problem


def _problem_to_summary_dto(problem: Problem) -> ProblemSummaryDTO:
    return ProblemSummaryDTO(
        problem_id=problem.problem_id,
        title=problem.title,
        created_by=problem.created_by,
        created_at=problem.created_at,
    )


def _problem_to_detail_dto(problem: Problem) -> ProblemDetailDTO:
    samples = [tc for tc in problem.test_cases if tc.is_sample]
    return ProblemDetailDTO(
        problem_id=problem.problem_id,
        title=problem.title,
        description=problem.description,
        time_limit_ms=problem.time_limit_ms,
        memory_limit_mb=problem.memory_limit_mb,
        created_by=problem.created_by,
        created_at=problem.created_at,
        sample_test_cases=[
            TestCaseDTO(
                test_case_id=tc.test_case_id,
                input=tc.input,
                expected_output=tc.expected_output,
                is_sample=tc.is_sample,
            )
            for tc in samples
        ],
    )


def _submission_to_dto(submission: Submission) -> SubmissionResponseDTO:
    return SubmissionResponseDTO(
        submission_id=submission.submission_id,
        problem_id=submission.problem_id,
        member_id=submission.member_id,
        language=submission.language,
        status=submission.status,
        score=submission.score,
        runtime_ms=submission.runtime_ms,
        memory_kb=submission.memory_kb,
        created_at=submission.created_at,
        updated_at=submission.updated_at,
    )
