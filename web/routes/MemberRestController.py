from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from core.response.ApiResponse import ApiResponse
from core.response.SuccessStatus import SuccessStatus
from service.MemberService.MemberService import MemberService

member_bp = Blueprint(
    "member",
    __name__,
    url_prefix="/api/member"
)

_service = MemberService()


@member_bp.route("/me", methods=["GET"])
@jwt_required()
def get_my_info():

    dto = _service.get_my_info()

    return ApiResponse.on_success(
        SuccessStatus.MEMBER_INFO_SUCCESS,
        dto
    )

@member_bp.route("/me", methods=["PUT"])
@jwt_required()
def update_my_info():

    data = request.get_json()

    email = data.get("email")
    address = data.get("address")
    car_num = data.get("car_num")
    department_name = data.get("department_name")
    work_type = data.get("work_type")

    dto = _service.update_my_info(
        email=email,
        address=address,
        car_num=car_num,
        department_name=department_name,
        work_type=work_type
    )

    return ApiResponse.on_success(
        SuccessStatus.MEMBER_UPDATE_SUCCESS,
        dto
    )

@member_bp.route("/search", methods=["GET"])
@jwt_required()
def search_members():

    keyword = request.args.get("keyword", "")
    department_id = request.args.get("department_id", "")

    dto_list = _service.search_members(keyword, department_id)

    return ApiResponse.on_success(
        SuccessStatus.MEMBER_SEARCH_SUCCESS,
        dto_list
    )

@member_bp.route("/departments", methods=["GET"])
@jwt_required()
def list_departments():

    dto_list = _service.list_departments()

    return ApiResponse.on_success(
        SuccessStatus.MEMBER_DEPARTMENT_LIST_SUCCESS,
        dto_list
    )