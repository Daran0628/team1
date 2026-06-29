from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt, jwt_required

from core.jwt.JwtUtils import role_required

todo_bp = Blueprint("todo", __name__, url_prefix="/api/todo")


@todo_bp.route("/all", methods=["GET"])
@jwt_required()
def all_users():
    """인증된 사용자 전체 접근"""
    claims = get_jwt()
    return jsonify({"isSuccess": True, "message": "전체 접근 성공", "role": claims.get("role")})


@todo_bp.route("/user", methods=["GET"])
@jwt_required()
@role_required("USER")
def user_only():
    """USER 전용"""
    return jsonify({"isSuccess": True, "message": "USER 전용 접근 성공"})


@todo_bp.route("/admin", methods=["GET"])
@jwt_required()
@role_required("ADMIN")
def admin_only():
    """ADMIN 전용"""
    return jsonify({"isSuccess": True, "message": "ADMIN 전용 접근 성공"})


@todo_bp.route("/user-admin", methods=["GET"])
@jwt_required()
@role_required("USER", "ADMIN")
def user_and_admin():
    """USER + ADMIN 접근"""
    return jsonify({"isSuccess": True, "message": "USER/ADMIN 접근 성공"})
