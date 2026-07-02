from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from core.response.ApiResponse import ApiResponse
from core.response.ErrorStatus import ErrorStatus
from core.response.SuccessStatus import SuccessStatus
from domain.model.Member import Member
import service.CodingTestService.CodingTestService as coding_test_service
from service.CodingTestService.CodingTestService import CodingTestException
from web.dto.CodingTestRequestDTO import (
    CreateProblemRequestDTO,
    TestCaseInputDTO,
    CreateSubmissionRequestDTO,
)

coding_test_bp = Blueprint('coding_test', __name__, url_prefix='/api/coding-test')

_ADMIN_ACCOUNT_TYPES = {'ADMIN', 'SUPERADMIN'}


def _current_member() -> Member | None:
    return Member.query.filter_by(account_id=get_jwt_identity()).first()


def _is_admin() -> bool:
    return get_jwt().get('role', '') in _ADMIN_ACCOUNT_TYPES


def _handle(fn):
    try:
        return fn()
    except CodingTestException as e:
        return ApiResponse.on_failure(e.error_status, e.detail)
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, str(e))
    except Exception as e:
        return ApiResponse.on_failure(ErrorStatus._INTERNAL_SERVER_ERROR, str(e))


# ── 문제 ─────────────────────────────────────────────────────────

@coding_test_bp.route('/problems', methods=['POST'])
@jwt_required()
def api_create_problem():
    if not _is_admin():
        return ApiResponse.on_failure(ErrorStatus._FORBIDDEN)

    body = request.get_json(silent=True) or {}

    def work():
        member = _current_member()
        if not member:
            return ApiResponse.on_failure(ErrorStatus.MEMBER_NOT_FOUND)

        dto = CreateProblemRequestDTO(
            title=body.get('title', ''),
            description=body.get('description', ''),
            difficulty=body.get('difficulty', 'BEGINNER'),
            time_limit_ms=int(body.get('timeLimitMs', 2000)),
            memory_limit_mb=int(body.get('memoryLimitMb', 256)),
            test_cases=[
                TestCaseInputDTO(
                    input=tc.get('input', ''),
                    expected_output=tc.get('expectedOutput', ''),
                    is_sample=bool(tc.get('isSample', False)),
                )
                for tc in body.get('testCases', [])
            ],
        )
        result = coding_test_service.create_problem(dto, created_by=member.id)
        return ApiResponse.on_success(SuccessStatus.CODE_PROBLEM_CREATE, result)
    return _handle(work)


@coding_test_bp.route('/problems', methods=['GET'])
@jwt_required()
def api_list_problems():
    def work():
        difficulty = request.args.get('difficulty')
        result = coding_test_service.list_problems(difficulty)
        return ApiResponse.on_success(SuccessStatus.CODE_PROBLEM_LIST, result)
    return _handle(work)


@coding_test_bp.route('/problems/<problem_id>', methods=['GET'])
@jwt_required()
def api_get_problem(problem_id: str):
    def work():
        result = coding_test_service.get_problem(problem_id)
        return ApiResponse.on_success(SuccessStatus.CODE_PROBLEM_READ, result)
    return _handle(work)


# ── 제출 ─────────────────────────────────────────────────────────

@coding_test_bp.route('/submissions', methods=['POST'])
@jwt_required()
def api_create_submission():
    body = request.get_json(silent=True) or {}

    def work():
        member = _current_member()
        if not member:
            return ApiResponse.on_failure(ErrorStatus.MEMBER_NOT_FOUND)

        dto = CreateSubmissionRequestDTO(
            problem_id=body.get('problemId', ''),
            language=body.get('language', ''),
            source_code=body.get('sourceCode', ''),
        )
        result = coding_test_service.create_submission(dto, member_id=member.id)
        return ApiResponse.on_success(SuccessStatus.CODE_SUBMISSION_CREATE, result)
    return _handle(work)


@coding_test_bp.route('/submissions/<submission_id>', methods=['GET'])
@jwt_required()
def api_get_submission(submission_id: str):
    def work():
        member = _current_member()
        if not member:
            return ApiResponse.on_failure(ErrorStatus.MEMBER_NOT_FOUND)
        result = coding_test_service.get_submission(submission_id, member.id, is_admin=_is_admin())
        return ApiResponse.on_success(SuccessStatus.CODE_SUBMISSION_READ, result)
    return _handle(work)


@coding_test_bp.route('/submissions', methods=['GET'])
@jwt_required()
def api_list_my_submissions():
    def work():
        member = _current_member()
        if not member:
            return ApiResponse.on_failure(ErrorStatus.MEMBER_NOT_FOUND)
        problem_id = request.args.get('problemId')
        result = coding_test_service.list_my_submissions(member.id, problem_id)
        return ApiResponse.on_success(SuccessStatus.CODE_SUBMISSION_LIST, result)
    return _handle(work)
