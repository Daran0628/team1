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
    MEMBER_NOT_FOUND                = (HTTPStatus.NOT_FOUND,   "MEMBER4001", "사용자가 존재하지 않습니다.")
    MEMBER_PASSWORD_NOT_MATCHED     = (HTTPStatus.BAD_REQUEST, "MEMBER4002", "비밀번호가 일치하지 않습니다.")
    MEMBER_TOKEN_NULL               = (HTTPStatus.FORBIDDEN,   "MEMBER4003", "액세스 토큰 또는 리프레시 토큰 값이 없습니다.")
    MEMBER_REFRESH_TOKEN_BLACKLIST  = (HTTPStatus.FORBIDDEN,   "MEMBER4004", "블랙리스트로 등록된 리프레시 토큰 입니다.")
    MEMBER_REFRESH_TOKEN_EXPIRED    = (HTTPStatus.FORBIDDEN,   "MEMBER4005", "만료된 리프레시 토큰 입니다.")
    MEMBER_REFRESH_TOKEN_INVALID    = (HTTPStatus.FORBIDDEN,   "MEMBER4006", "유효한 액세스 토큰이 아닙니다.")

    # RBAC
    RBAC_ROLE_NOT_FOUND             = (HTTPStatus.NOT_FOUND,   "RBAC4001", "역할을 찾을 수 없습니다.")
    RBAC_ROLE_NAME_DUPLICATE        = (HTTPStatus.CONFLICT,    "RBAC4002", "이미 존재하는 역할 이름입니다.")
    RBAC_ROLE_HAS_BINDINGS          = (HTTPStatus.CONFLICT,    "RBAC4003", "해당 역할에 바인딩된 대상이 있어 삭제할 수 없습니다.")
    RBAC_PERMISSION_NOT_FOUND       = (HTTPStatus.NOT_FOUND,   "RBAC4011", "권한을 찾을 수 없습니다.")
    RBAC_PERMISSION_DUPLICATE       = (HTTPStatus.CONFLICT,    "RBAC4012", "이미 존재하는 권한입니다.")
    RBAC_PERMISSION_ALREADY_ASSIGNED = (HTTPStatus.CONFLICT,   "RBAC4013", "이미 역할에 할당된 권한입니다.")
    RBAC_BINDING_NOT_FOUND           = (HTTPStatus.NOT_FOUND,   "RBAC4021", "역할 바인딩을 찾을 수 없습니다.")
    RBAC_BINDING_ALREADY_EXISTS      = (HTTPStatus.CONFLICT,    "RBAC4022", "이미 존재하는 역할 바인딩입니다.")

    # Storage (MinIO 오브젝트 스토리지)
    STORAGE_BUCKET_NOT_FOUND      = (HTTPStatus.NOT_FOUND,  "STORAGE4001", "버켓을 찾을 수 없습니다.")
    STORAGE_BUCKET_ALREADY_EXISTS = (HTTPStatus.CONFLICT,   "STORAGE4002", "이미 존재하는 버켓입니다.")
    STORAGE_BUCKET_NOT_EMPTY      = (HTTPStatus.CONFLICT,   "STORAGE4003", "버켓이 비어있지 않습니다. ?force=true로 강제 삭제하세요.")
    STORAGE_OBJECT_NOT_FOUND      = (HTTPStatus.NOT_FOUND,  "STORAGE4011", "오브젝트를 찾을 수 없습니다.")
    STORAGE_FOLDER_NOT_EMPTY      = (HTTPStatus.CONFLICT,   "STORAGE4012", "폴더가 비어있지 않습니다.")
    STORAGE_FILE_TOO_LARGE        = (HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "STORAGE4013", "파일 크기는 최대 200MB까지 업로드할 수 있습니다.")
    STORAGE_OPERATION_FAILED      = (HTTPStatus.INTERNAL_SERVER_ERROR, "STORAGE5001", "스토리지 작업에 실패했습니다.")

    # Group (커스텀 그룹)
    GROUP_NOT_FOUND                  = (HTTPStatus.NOT_FOUND,   "GROUP4001", "그룹을 찾을 수 없습니다.")
    GROUP_NAME_DUPLICATE             = (HTTPStatus.CONFLICT,    "GROUP4002", "이미 존재하는 그룹 이름입니다.")
    GROUP_MEMBER_NOT_FOUND           = (HTTPStatus.NOT_FOUND,   "GROUP4003", "그룹에서 해당 멤버를 찾을 수 없습니다.")
    GROUP_MEMBER_ALREADY_EXISTS      = (HTTPStatus.CONFLICT,    "GROUP4004", "이미 그룹에 속한 멤버입니다.")

    # VDI (가상 데스크탑)
    VDI_NOT_FOUND              = (HTTPStatus.NOT_FOUND,            "VDI4001", "VDI 인스턴스를 찾을 수 없습니다.")
    VDI_ALREADY_EXISTS         = (HTTPStatus.CONFLICT,             "VDI4002", "이미 존재하는 컨테이너 이름입니다.")
    VDI_MEMBER_ALREADY_HAS_VDI = (HTTPStatus.CONFLICT,             "VDI4003", "이미 VDI가 할당된 사용자입니다.")
    VDI_SNAPSHOT_NOT_FOUND     = (HTTPStatus.NOT_FOUND,            "VDI4004", "스냅샷을 찾을 수 없습니다.")
    VDI_INVALID_SNAPSHOT_NAME  = (HTTPStatus.BAD_REQUEST,          "VDI4005", "스냅샷 이름은 영문 소문자, 숫자, '.', '_', '-'만 사용할 수 있습니다.")
    VDI_CREATE_FAILED          = (HTTPStatus.INTERNAL_SERVER_ERROR, "VDI5001", "컨테이너 생성에 실패했습니다.")
    VDI_OPERATION_FAILED       = (HTTPStatus.INTERNAL_SERVER_ERROR, "VDI5002", "컨테이너 작업에 실패했습니다.")
    
    # Board (게시판)
    BOARD_NOT_FOUND                  = (HTTPStatus.NOT_FOUND,  "BOARD4001", "게시판을 찾을 수 없습니다.")
    BOARD_ACCESS_DENIED              = (HTTPStatus.FORBIDDEN,  "BOARD4002", "게시판 접근 권한이 없습니다.")
    POST_NOT_FOUND                   = (HTTPStatus.NOT_FOUND,  "BOARD4011", "게시글을 찾을 수 없습니다.")
    POST_NOT_AUTHOR                  = (HTTPStatus.FORBIDDEN,  "BOARD4012", "게시글 작성자가 아닙니다.")
    POST_ALREADY_PROCESSED           = (HTTPStatus.CONFLICT,   "BOARD4013", "이미 처리된 게시글입니다.")
    COMMENT_NOT_FOUND                = (HTTPStatus.NOT_FOUND,  "BOARD4021", "댓글을 찾을 수 없습니다.")
    COMMENT_NOT_AUTHOR               = (HTTPStatus.FORBIDDEN,  "BOARD4022", "댓글 작성자가 아닙니다.")
    BOARD_APPROVER_NOT_FOUND         = (HTTPStatus.NOT_FOUND,  "BOARD4031", "승인자를 찾을 수 없습니다.")
    BOARD_APPROVER_ALREADY_EXISTS    = (HTTPStatus.CONFLICT,   "BOARD4032", "이미 등록된 승인자입니다.")
    BOARD_APPROVAL_PERMISSION_DENIED = (HTTPStatus.FORBIDDEN,  "BOARD4033", "게시글 승인 권한이 없습니다.")
    ATTACHMENT_NOT_FOUND             = (HTTPStatus.NOT_FOUND,  "BOARD4041", "첨부파일을 찾을 수 없습니다.")
    ATTACHMENT_TOO_LARGE             = (HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "BOARD4042", "파일 하나의 크기는 최대 50MB까지 업로드할 수 있습니다.")
    ATTACHMENT_TOTAL_TOO_LARGE       = (HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "BOARD4043", "한 번에 업로드 가능한 첨부파일 총 용량은 150MB입니다.")
    ATTACHMENT_UPLOAD_FAILED         = (HTTPStatus.INTERNAL_SERVER_ERROR, "BOARD5001", "첨부파일 업로드에 실패했습니다.")

    # Group (커스텀 그룹)
    GROUP_NOT_FOUND                  = (HTTPStatus.NOT_FOUND,   "GROUP4001", "그룹을 찾을 수 없습니다.")
    GROUP_NAME_DUPLICATE             = (HTTPStatus.CONFLICT,    "GROUP4002", "이미 존재하는 그룹 이름입니다.")
    GROUP_MEMBER_NOT_FOUND           = (HTTPStatus.NOT_FOUND,   "GROUP4003", "그룹에서 해당 멤버를 찾을 수 없습니다.")
    GROUP_MEMBER_ALREADY_EXISTS      = (HTTPStatus.CONFLICT,    "GROUP4004", "이미 그룹에 속한 멤버입니다.")

    # VDI (가상 데스크탑)
    VDI_NOT_FOUND              = (HTTPStatus.NOT_FOUND,            "VDI4001", "VDI 인스턴스를 찾을 수 없습니다.")
    VDI_ALREADY_EXISTS         = (HTTPStatus.CONFLICT,             "VDI4002", "이미 존재하는 컨테이너 이름입니다.")
    VDI_MEMBER_ALREADY_HAS_VDI = (HTTPStatus.CONFLICT,             "VDI4003", "이미 VDI가 할당된 사용자입니다.")
    VDI_CREATE_FAILED          = (HTTPStatus.INTERNAL_SERVER_ERROR, "VDI5001", "컨테이너 생성에 실패했습니다.")
    VDI_OPERATION_FAILED       = (HTTPStatus.INTERNAL_SERVER_ERROR, "VDI5002", "컨테이너 작업에 실패했습니다.")

    # Chat
    CHAT_ROOM_NOT_FOUND        = (HTTPStatus.NOT_FOUND,  "CHAT4001", "채팅방을 찾을 수 없습니다.")
    CHAT_NOT_A_MEMBER          = (HTTPStatus.FORBIDDEN,  "CHAT4002", "채팅방 멤버가 아닙니다.")
    CHAT_ALREADY_A_MEMBER      = (HTTPStatus.CONFLICT,   "CHAT4003", "이미 채팅방 멤버입니다.")
    CHAT_DIRECT_ALREADY_EXISTS = (HTTPStatus.CONFLICT,   "CHAT4004", "이미 존재하는 1:1 채팅방입니다.")
    CHAT_PERMISSION_DENIED     = (HTTPStatus.FORBIDDEN,  "CHAT4005", "채팅방 관리 권한이 없습니다.")
    CHAT_ADMIN_MUST_TRANSFER   = (HTTPStatus.CONFLICT,   "CHAT4006", "관리자는 다른 멤버에게 관리자를 이양 후 나가야 합니다.")
    CHAT_MESSAGE_NOT_FOUND     = (HTTPStatus.NOT_FOUND,  "CHAT4011", "메시지를 찾을 수 없습니다.")
    CHAT_FILE_NOT_FOUND        = (HTTPStatus.NOT_FOUND,  "CHAT4012", "첨부 파일을 찾을 수 없습니다.")
    CHAT_FILE_TOO_LARGE        = (HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "CHAT4013", "파일 크기는 최대 25MB까지 업로드할 수 있습니다.")
    CHAT_FILE_UPLOAD_FAILED    = (HTTPStatus.INTERNAL_SERVER_ERROR, "CHAT5001", "파일 업로드에 실패했습니다.")

    # Cafeteria
    CAFETERIA_MENU_NOT_FOUND = (HTTPStatus.NOT_FOUND, "CAFETERIA4001", "해당 날짜의 메뉴가 없습니다.")


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
