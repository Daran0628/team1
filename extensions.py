import os
from datetime import timedelta

from flask import jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager

from redis_client import is_token_blacklisted

bcrypt = Bcrypt()
jwt = JWTManager()


def init_extensions(app):
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_EXPIRES_MIN", 15))
    )
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(
        days=int(os.getenv("JWT_REFRESH_EXPIRES_DAYS", 7))
    )

    bcrypt.init_app(app)
    jwt.init_app(app)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        return is_token_blacklisted(jwt_payload["jti"])

    @jwt.revoked_token_loader
    def revoked_token_response(jwt_header, jwt_payload):
        return jsonify({"msg": "토큰이 무효화되었습니다. 다시 로그인해주세요."}), 401

    @jwt.expired_token_loader
    def expired_token_response(jwt_header, jwt_payload):
        return jsonify({"msg": "토큰이 만료되었습니다."}), 401

    @jwt.invalid_token_loader
    def invalid_token_response(error):
        return jsonify({"msg": "유효하지 않은 토큰입니다."}), 422

    @jwt.unauthorized_loader
    def missing_token_response(error):
        return jsonify({"msg": "인증 토큰이 필요합니다."}), 401
