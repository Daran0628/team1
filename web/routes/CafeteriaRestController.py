from datetime import date

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt

from core.response.ApiResponse import ApiResponse
from core.response.ErrorStatus import ErrorStatus
from core.response.SuccessStatus import SuccessStatus
from domain.model.Member import Member
from service.CafeteriaService.CafeteriaService import CafeteriaService
from web.converter.CafeteriaConverter import CafeteriaConverter

cafeteria_bp = Blueprint("cafeteria", __name__, url_prefix="/api/cafeteria")
_service = CafeteriaService()

_ADMIN_ROLES = ("ADMIN", "SUPERADMIN")


@cafeteria_bp.route("/today", methods=["GET"])
@jwt_required()
def get_today_menu():
    menu = _service.get_today_menu()
    if not menu:
        return ApiResponse.on_failure(ErrorStatus.CAFETERIA_MENU_NOT_FOUND, None)
    dto = CafeteriaConverter.to_menu_item_dto(menu)
    return ApiResponse.on_success(SuccessStatus.CAFETERIA_MENU_TODAY, dto)


@cafeteria_bp.route("/month", methods=["GET"])
@jwt_required()
def get_month_menus():
    today = date.today()
    year = request.args.get("year", today.year, type=int)
    month = request.args.get("month", today.month, type=int)
    menus = _service.get_month_menus(year, month)
    dto = CafeteriaConverter.to_month_dto(year, month, menus)
    return ApiResponse.on_success(SuccessStatus.CAFETERIA_MENU_MONTH, dto)


@cafeteria_bp.route("/recommend", methods=["GET"])
@jwt_required()
def recommend_lunch():
    result = _service.recommend_lunch()
    dto = CafeteriaConverter.to_recommend_dto(result)
    return ApiResponse.on_success(SuccessStatus.CAFETERIA_LUNCH_RECOMMEND, dto)


@cafeteria_bp.route("", methods=["POST"])
@jwt_required()
def upsert_menu():
    claims = get_jwt()
    if claims.get("role") not in _ADMIN_ROLES:
        return ApiResponse.on_failure(ErrorStatus._FORBIDDEN, None)

    body = request.get_json() or {}
    menu_date_str = body.get("menu_date")
    menu_text = body.get("menu_text")
    if not menu_date_str or not menu_text:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, None)

    menu_date = date.fromisoformat(menu_date_str)
    account_id = claims.get("sub")
    member = Member.query.filter_by(account_id=account_id).first()
    member_id = member.id if member else None
    menu = _service.upsert_menu(menu_date, menu_text, member_id)
    dto = CafeteriaConverter.to_menu_item_dto(menu)
    return ApiResponse.on_success(SuccessStatus.CAFETERIA_MENU_UPSERT, dto)


@cafeteria_bp.route("/<menu_date_str>", methods=["DELETE"])
@jwt_required()
def delete_menu(menu_date_str):
    claims = get_jwt()
    if claims.get("role") not in _ADMIN_ROLES:
        return ApiResponse.on_failure(ErrorStatus._FORBIDDEN, None)

    menu_date = date.fromisoformat(menu_date_str)
    ok = _service.delete_menu(menu_date)
    if not ok:
        return ApiResponse.on_failure(ErrorStatus.CAFETERIA_MENU_NOT_FOUND, None)
    return ApiResponse.on_success(SuccessStatus.CAFETERIA_MENU_DELETE, None)
