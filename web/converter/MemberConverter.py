from datetime import datetime, timezone

from domain.model.Member import Member
from web.dto.AuthResponseDTO import LoginResponseDTO, LogoutResponseDTO


class MemberConverter:

    @staticmethod
    def to_login_response_dto(member: Member, access_token: str) -> LoginResponseDTO:
        return LoginResponseDTO(
            access_token=access_token,
            name_ko=member.name_ko,
            account_id=member.account_id,
            employee_no=member.employee_no,
            dept_path_name=member.dept_path_name,
            enrollment_status=member.enrollment_status,
            account_type=member.account_type,
        )

    @staticmethod
    def to_logout_response_dto() -> LogoutResponseDTO:
        return LogoutResponseDTO(
            logout_at=datetime.now(timezone.utc),
        )
