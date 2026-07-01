from flask_jwt_extended import get_jwt_identity

from domain.model.Member import Member
from domain.model.Department import Department
from domain.enum.EnrollmentStatus import EnrollmentStatus
from web.converter.MemberConverter import MemberConverter
from web.dto.MemberResponseDTO import DepartmentOptionDTO
from extensions import db


class MemberService:

    def get_my_info(self):

        account_id = get_jwt_identity()

        member = Member.query.filter_by(
            account_id=account_id
        ).first()

        if member is None:
            raise ValueError("존재하지 않는 회원입니다.")

        return MemberConverter.to_member_info_response_dto(member)

    def update_my_info(self, email, address, car_num, department_name, work_type):

        account_id = get_jwt_identity()

        member = Member.query.filter_by(
            account_id=account_id
        ).first()

        if member is None:
            raise ValueError("존재하지 않는 회원입니다.")

        # =========================
        # 변경 가능한 필드만 업데이트
        # =========================
        if email is not None:
            member.email = email

        if address is not None:
            member.address = address

        if car_num is not None:
            member.car_num = car_num

        if department_name is not None:
            member.department_name = department_name

        if work_type is not None:
            member.work_type = work_type

        # DB 반영
        db.session.commit()

        # DTO로 반환 (GET과 동일한 응답 구조 유지 추천)
        return MemberConverter.to_member_info_response_dto(member)

    def search_members(self, keyword: str, department_id: str = None):

        keyword = (keyword or "").strip()
        department_id = (department_id or "").strip()

        if not keyword and not department_id:
            return []

        filters = [Member.enrollment_status == EnrollmentStatus.ACTIVE]

        if keyword:
            filters.append(Member.name_ko.ilike(f"%{keyword}%"))

        if department_id:
            filters.append(Member.department_id == department_id)

        members = Member.query.filter(*filters).all()

        return [MemberConverter.to_search_result_dto(m) for m in members]

    def list_departments(self):

        departments = Department.query.order_by(Department.department_name).all()

        return [
            DepartmentOptionDTO(department_id=d.id, department_name=d.department_name)
            for d in departments
        ]