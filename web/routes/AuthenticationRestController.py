import logging
import os

from flask import Blueprint, make_response, request
from flask_jwt_extended import decode_token

from core.response.ApiResponse import ApiResponse
from core.response.ErrorStatus import ErrorStatus
from core.response.SuccessStatus import SuccessStatus
from service.AuthenticationService.AuthenticationService import AuthenticationService
from web.dto.AuthRequestDTO import LoginRequestDTO
from web.dto.AuthResponseDTO import RefreshResponseDTO

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
_service = AuthenticationService()

_REFRESH_MAX_AGE = int(os.getenv("JWT_REFRESH_EXPIRES_DAYS", 7)) * 24 * 60 * 60


def _set_refresh_cookie(response, token: str) -> None:
    """Refresh token → HttpOnly Cookie"""
    response.set_cookie(
        "refreshToken",
        token,
        max_age=_REFRESH_MAX_AGE,
        httponly=True,
        samesite="Lax",
        secure=os.getenv("JWT_COOKIE_SECURE", "false").lower() == "true",
    )


def _clear_refresh_cookie(response) -> None:
    response.set_cookie("refreshToken", "", max_age=0, httponly=True, samesite="Lax")


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    try:
        request_dto = LoginRequestDTO(
            account_id=data.get("accountId", ""),
            password=data.get("password", ""),
        )
    except ValueError as e:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, str(e))

    try:
        login_dto, refresh_token = _service.login(request_dto)
    except ValueError as e:
        msg = str(e)
        if "존재하지 않는" in msg:
            return ApiResponse.on_failure(ErrorStatus.MEMBER_NOT_FOUND)
        if "비밀번호" in msg:
            return ApiResponse.on_failure(ErrorStatus.MEMBER_PASSWORD_NOT_MATCHED)
        return ApiResponse.on_failure(ErrorStatus._INTERNAL_SERVER_ERROR)

    # access_token → JSON body, refresh_token → HttpOnly Cookie
    resp = make_response(*ApiResponse.on_success(SuccessStatus.MEMBER_LOGIN_SUCCESS, login_dto))
    _set_refresh_cookie(resp, refresh_token)
    return resp


@auth_bp.route("/logout", methods=["GET"])
def logout():
    """Cookie의 refresh token을 블랙리스트 등록 후 쿠키 삭제"""
    refresh_token = request.cookies.get("refreshToken")
    if not refresh_token:
        return ApiResponse.on_failure(ErrorStatus.MEMBER_TOKEN_NULL)

    try:
        claims = decode_token(refresh_token, allow_expired=True)
    except Exception as e:
        logger.warning("logout — token decode failed: %s", e)
        resp = make_response(*ApiResponse.on_failure(ErrorStatus._UNAUTHORIZED))
        _clear_refresh_cookie(resp)
        return resp

    result = _service.logout(jti=claims["jti"], exp=claims["exp"])
    resp = make_response(*ApiResponse.on_success(SuccessStatus.MEMBER_LOGOUT_SUCCESS, result))
    _clear_refresh_cookie(resp)
    return resp


@auth_bp.route("/refresh", methods=["GET"])
def refresh_access_token():
    """Cookie의 refresh token으로 새 access/refresh token 발급 (rotation)"""
    refresh_token = request.cookies.get("refreshToken")
    if not refresh_token:
        return ApiResponse.on_failure(ErrorStatus.MEMBER_TOKEN_NULL)

    try:
        claims = decode_token(refresh_token)
    except Exception as e:
        logger.warning("refresh — token decode failed: %s", e)
        return ApiResponse.on_failure(ErrorStatus.MEMBER_REFRESH_TOKEN_INVALID)

    try:
        new_access_token, new_refresh_token = _service.recreate_token(
            identity=claims["sub"],
            role=claims.get("role", ""),
            old_jti=claims["jti"],
            old_exp=claims["exp"],
        )
    except ValueError as e:
        msg = str(e)
        if "블랙리스트" in msg:
            return ApiResponse.on_failure(ErrorStatus.MEMBER_REFRESH_TOKEN_BLACKLIST)
        return ApiResponse.on_failure(ErrorStatus.MEMBER_REFRESH_TOKEN_INVALID)

    # 새 access_token → JSON body, 새 refresh_token → Cookie (rotation)
    resp = make_response(*ApiResponse.on_success(
        SuccessStatus.MEMBER_REFRESH_TOKEN_SUCCESS,
        RefreshResponseDTO(access_token=new_access_token),
    ))
    _set_refresh_cookie(resp, new_refresh_token)
    return resp
