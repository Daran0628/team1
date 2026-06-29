from flask_jwt_extended import get_jwt_identity

from domain.model.Member import Member
from web.converter.MemberConverter import MemberConverter
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