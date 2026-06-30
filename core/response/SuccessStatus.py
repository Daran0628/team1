from http import HTTPStatus
from enum import Enum

from core.response.ReasonDTO import ReasonDTO


class SuccessStatus(Enum):
    _OK                          = (HTTPStatus.OK,      "COMMON200",  "성공입니다.")
    MEMBER_LOGIN_SUCCESS         = (HTTPStatus.OK,      "MEMBER2001", "로그인에 성공했습니다.")
    MEMBER_LOGOUT_SUCCESS        = (HTTPStatus.OK,      "MEMBER2002", "로그아웃에 성공했습니다.")
    MEMBER_REFRESH_TOKEN_SUCCESS = (HTTPStatus.CREATED, "MEMBER2004", "토큰 재발급을 성공했습니다.")
    MEMBER_INFO_SUCCESS          = (HTTPStatus.OK,      "MEMBER2005", "회원 정보를 조회했습니다.")
    MEMBER_UPDATE_SUCCESS        = (HTTPStatus.OK,      "MEMBER2006", "회원 정보를 수정했습니다.")

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

    # Storage (MinIO 오브젝트 스토리지)
    STORAGE_BUCKET_CREATE  = (HTTPStatus.CREATED, "STORAGE2001", "버켓이 생성되었습니다.")
    STORAGE_BUCKET_READ    = (HTTPStatus.OK,      "STORAGE2002", "버켓 조회에 성공했습니다.")
    STORAGE_BUCKET_DELETE  = (HTTPStatus.OK,      "STORAGE2003", "버켓이 삭제되었습니다.")
    STORAGE_OBJECT_LIST    = (HTTPStatus.OK,      "STORAGE2011", "오브젝트 목록 조회에 성공했습니다.")
    STORAGE_OBJECT_UPLOAD  = (HTTPStatus.CREATED, "STORAGE2012", "오브젝트 업로드에 성공했습니다.")
    STORAGE_OBJECT_STAT    = (HTTPStatus.OK,      "STORAGE2013", "오브젝트 정보를 조회했습니다.")
    STORAGE_OBJECT_DELETE  = (HTTPStatus.OK,      "STORAGE2014", "오브젝트가 삭제되었습니다.")
    STORAGE_OBJECT_COPY    = (HTTPStatus.OK,      "STORAGE2015", "오브젝트가 복사되었습니다.")
    STORAGE_OBJECT_URL       = (HTTPStatus.OK,      "STORAGE2016", "Presigned URL이 생성되었습니다.")
    STORAGE_OBJECT_SHARE_URL = (HTTPStatus.OK,      "STORAGE2017", "공유 URL이 생성되었습니다.")
    STORAGE_OBJECT_TAGS_GET    = (HTTPStatus.OK,  "STORAGE2021", "태그 조회에 성공했습니다.")
    STORAGE_OBJECT_TAGS_SET    = (HTTPStatus.OK,  "STORAGE2022", "태그가 설정되었습니다.")
    STORAGE_OBJECT_TAGS_DELETE = (HTTPStatus.OK,  "STORAGE2023", "태그가 삭제되었습니다.")

    # Group (커스텀 그룹)
    GROUP_CREATE        = (HTTPStatus.CREATED, "GROUP2001", "그룹이 생성되었습니다.")
    GROUP_READ          = (HTTPStatus.OK,      "GROUP2002", "그룹 조회에 성공했습니다.")
    GROUP_UPDATE        = (HTTPStatus.OK,      "GROUP2003", "그룹이 수정되었습니다.")
    GROUP_DELETE        = (HTTPStatus.OK,      "GROUP2004", "그룹이 삭제되었습니다.")
    GROUP_MEMBER_ADD    = (HTTPStatus.OK,      "GROUP2005", "그룹에 멤버가 추가되었습니다.")
    GROUP_MEMBER_REMOVE = (HTTPStatus.OK,      "GROUP2006", "그룹에서 멤버가 제거되었습니다.")

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
