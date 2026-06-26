from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)

from auth.models import find_user_by_email, verify_password
from redis_client import add_token_to_blacklist

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _ttl(exp: int) -> int:
    """토큰 만료까지 남은 초 + 60초 버퍼 (clock skew 대응)."""
    return max(int(exp - datetime.now(timezone.utc).timestamp()), 0) + 60


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"msg": "이메일과 비밀번호를 입력해주세요."}), 400

    user = find_user_by_email(email)
    if not user or not verify_password(user, password):
        return jsonify({"msg": "이메일 또는 비밀번호가 올바르지 않습니다."}), 401

    claims = {"role": user["role"], "name": user["name"]}
    access_token = create_access_token(identity=str(user["id"]), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(user["id"]), additional_claims=claims)

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {"id": user["id"], "name": user["name"], "role": user["role"]},
    }), 200


@auth_bp.route("/logout", methods=["DELETE"])
@jwt_required()
def logout():
    jwt_data = get_jwt()
    add_token_to_blacklist(jwt_data["jti"], _ttl(jwt_data["exp"]))
    return jsonify({"msg": "로그아웃 되었습니다."}), 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    jwt_data = get_jwt()

    # refresh token rotation: 사용한 refresh token 즉시 블랙리스트 처리
    add_token_to_blacklist(jwt_data["jti"], _ttl(jwt_data["exp"]))

    claims = {"role": jwt_data.get("role"), "name": jwt_data.get("name")}
    identity = get_jwt_identity()

    return jsonify({
        "access_token": create_access_token(identity=identity, additional_claims=claims),
        "refresh_token": create_refresh_token(identity=identity, additional_claims=claims),
    }), 200
