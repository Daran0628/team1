from http import HTTPStatus
from enum import Enum

from core.response.ErrorReasonDTO import ErrorReasonDTO


class ErrorStatus(Enum):
    # 공통
    _INTERNAL_SERVER_ERROR = (HTTPStatus.INTERNAL_SERVER_ERROR, "COMMON500", "서버 에러, 관리자에게 문의 바랍니다.")
    _BAD_REQUEST           = (HTTPStatus.BAD_REQUEST,           "COMMON400", "잘못된 요청입니다.")
    _UNAUTHORIZED          = (HTTPStatus.UNAUTHORIZED,          "COMMON401", "인증이 필요합니다.")
    _FORBIDDEN             = (HTTPStatus.FORBIDDEN,             "COMMON403", "금지된 요청입니다.")

    # 멤버
    MEMBER_NOT_FOUND                = (HTTPStatus.NOT_FOUND,  "MEMBER4001", "사용자가 존재하지 않습니다.")
    MEMBER_PASSWORD_NOT_MATCHED     = (HTTPStatus.BAD_REQUEST, "MEMBER4002", "비밀번호가 일치하지 않습니다.")
    MEMBER_TOKEN_NULL               = (HTTPStatus.FORBIDDEN,  "MEMBER4003", "액세스 토큰 또는 리프레시 토큰 값이 없습니다.")
    MEMBER_REFRESH_TOKEN_BLACKLIST  = (HTTPStatus.FORBIDDEN,  "MEMBER4004", "블랙리스트로 등록된 리프레시 토큰 입니다.")
    MEMBER_REFRESH_TOKEN_EXPIRED    = (HTTPStatus.FORBIDDEN,  "MEMBER4005", "만료된 리프레시 토큰 입니다.")
    MEMBER_REFRESH_TOKEN_INVALID    = (HTTPStatus.FORBIDDEN,  "MEMBER4006", "유효한 액세스 토큰이 아닙니다.")

    def __new__(cls, http_status: HTTPStatus, code: str, message: str):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.http_status = http_status
        obj.code = code
        obj.message = message
        return obj

    def get_reason(self) -> ErrorReasonDTO:
        return ErrorReasonDTO(is_success=False, code=self.code, message=self.message)

    def get_reason_http_status(self) -> ErrorReasonDTO:
        return ErrorReasonDTO(is_success=False, code=self.code, message=self.message, http_status=self.http_status)
