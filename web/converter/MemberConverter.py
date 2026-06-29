from datetime import datetime, timezone

from domain.model.Member import Member
from web.dto.AuthResponseDTO import LoginResponseDTO, LogoutResponseDTO
from web.dto.MemberResponseDTO import MemberInfoResponseDTO


class MemberConverter:

    @staticmethod
    def to_login_response_dto(member: Member, access_token: str) -> LoginResponseDTO:
        return LoginResponseDTO(
            access_token=access_token,
            name_ko=member.name_ko,
            account_id=member.account_id,
            employee_no=member.employee_no,
            department_id=member.department_id,
            enrollment_status=member.enrollment_status,
            account_type=member.account_type,
        )

    @staticmethod
    def to_logout_response_dto() -> LogoutResponseDTO:
        return LogoutResponseDTO(
            logout_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def to_member_info_response_dto(member: Member):

        return MemberInfoResponseDTO(
            account_id=member.account_id,
            name_ko=member.name_ko,
            employee_no=member.employee_no,

            department_name=member.department.department_name,

            email=member.email,
            address=member.address,
            car_num=member.car_num,

            account_type=member.account_type.value,
            work_type=member.work_type.value,

            last_login=member.last_login
        )
