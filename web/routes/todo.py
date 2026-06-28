from functools import wraps

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt, jwt_required

todo_bp = Blueprint("todo", __name__, url_prefix="/api/todo")


def _role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            if claims.get("role") not in roles:
                return jsonify({"isSuccess": False, "message": "접근 권한이 없습니다."}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


@todo_bp.route("/all", methods=["GET"])
@jwt_required()
def all_users():
    """인증된 사용자 전체 접근"""
    claims = get_jwt()
    return jsonify({"isSuccess": True, "message": "전체 접근 성공", "role": claims.get("role")})


@todo_bp.route("/user", methods=["GET"])
@jwt_required()
@_role_required("USER")
def user_only():
    """USER 전용"""
    return jsonify({"isSuccess": True, "message": "USER 전용 접근 성공"})


@todo_bp.route("/admin", methods=["GET"])
@jwt_required()
@_role_required("ADMIN")
def admin_only():
    """ADMIN 전용"""
    return jsonify({"isSuccess": True, "message": "ADMIN 전용 접근 성공"})


@todo_bp.route("/user-admin", methods=["GET"])
@jwt_required()
@_role_required("USER", "ADMIN")
def user_and_admin():
    """USER + ADMIN 접근"""
    return jsonify({"isSuccess": True, "message": "USER/ADMIN 접근 성공"})
