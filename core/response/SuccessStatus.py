from http import HTTPStatus
from enum import Enum

from core.response.ReasonDTO import ReasonDTO


class SuccessStatus(Enum):
    _OK                          = (HTTPStatus.OK,      "COMMON200",  "성공입니다.")
    MEMBER_LOGIN_SUCCESS         = (HTTPStatus.OK,      "MEMBER2001", "로그인에 성공했습니다.")
    MEMBER_LOGOUT_SUCCESS        = (HTTPStatus.OK,      "MEMBER2002", "로그아웃에 성공했습니다.")
    MEMBER_REFRESH_TOKEN_SUCCESS = (HTTPStatus.CREATED, "MEMBER2004", "토큰 재발급을 성공했습니다.")

    def __new__(cls, http_status: HTTPStatus, code: str, message: str):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.http_status = http_status
        obj.code = code
        obj.message = message
        return obj

    def get_reason(self) -> ReasonDTO:
        return ReasonDTO(is_success=True, code=self.code, message=self.message)

    def get_reason_http_status(self) -> ReasonDTO:
        return ReasonDTO(is_success=True, code=self.code, message=self.message, http_status=self.http_status)
