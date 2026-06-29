from http import HTTPStatus
from enum import Enum

from core.response.ReasonDTO import ReasonDTO


class SuccessStatus(Enum):
    _OK                          = (HTTPStatus.OK,      "COMMON200",  "성공입니다.")
    MEMBER_LOGIN_SUCCESS         = (HTTPStatus.OK,      "MEMBER2001", "로그인에 성공했습니다.")
    MEMBER_LOGOUT_SUCCESS        = (HTTPStatus.OK,      "MEMBER2002", "로그아웃에 성공했습니다.")
    MEMBER_REFRESH_TOKEN_SUCCESS = (HTTPStatus.CREATED, "MEMBER2004", "토큰 재발급을 성공했습니다.")

    # RBAC - Role
    RBAC_ROLE_CREATE  = (HTTPStatus.CREATED, "RBAC2001", "역할이 생성되었습니다.")
    RBAC_ROLE_READ    = (HTTPStatus.OK,      "RBAC2002", "역할 조회에 성공했습니다.")
    RBAC_ROLE_UPDATE  = (HTTPStatus.OK,      "RBAC2003", "역할이 수정되었습니다.")
    RBAC_ROLE_DELETE  = (HTTPStatus.OK,      "RBAC2004", "역할이 삭제되었습니다.")

    # RBAC - Permission
    RBAC_PERMISSION_CREATE  = (HTTPStatus.CREATED, "RBAC2011", "권한이 생성되었습니다.")
    RBAC_PERMISSION_READ    = (HTTPStatus.OK,      "RBAC2012", "권한 조회에 성공했습니다.")
    RBAC_PERMISSION_DELETE  = (HTTPStatus.OK,      "RBAC2013", "권한이 삭제되었습니다.")
    RBAC_PERMISSION_ASSIGN  = (HTTPStatus.OK,      "RBAC2014", "역할에 권한이 할당되었습니다.")
    RBAC_PERMISSION_REVOKE  = (HTTPStatus.OK,      "RBAC2015", "역할에서 권한이 회수되었습니다.")

    # RBAC - RoleBinding
    RBAC_BINDING_CREATE = (HTTPStatus.CREATED, "RBAC2021", "역할 바인딩이 생성되었습니다.")
    RBAC_BINDING_READ   = (HTTPStatus.OK,      "RBAC2022", "역할 바인딩 조회에 성공했습니다.")
    RBAC_BINDING_UPDATE = (HTTPStatus.OK,      "RBAC2023", "역할 바인딩이 수정되었습니다.")
    RBAC_BINDING_DELETE = (HTTPStatus.OK,      "RBAC2024", "역할 바인딩이 삭제되었습니다.")

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
