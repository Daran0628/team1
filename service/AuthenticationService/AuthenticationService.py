import logging
from datetime import datetime, timezone

from flask_bcrypt import check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token

from core.config.RedisConfig import redis_client
from domain.model.member import Member
from web.converter.member_converter import MemberConverter
from web.dto.auth_request_dto import LoginRequestDTO
from web.dto.auth_response_dto import LoginResponseDTO, LogoutResponseDTO

logger = logging.getLogger(__name__)

_BLACKLIST_PREFIX = "blacklist:"
_BLACKLIST_VALUE  = "revoked"


class AuthenticationService:

    def login(self, request_dto: LoginRequestDTO) -> tuple:
        """Returns (LoginResponseDTO, refresh_token: str)"""
        member: Member | None = Member.query.filter_by(
            account_id=request_dto.account_id
        ).first()
        if member is None:
            raise ValueError("존재하지 않는 사원입니다.")

        if not check_password_hash(member.password, request_dto.password):
            raise ValueError("비밀번호가 일치하지 않습니다.")

        additional_claims = {"role": member.account_type.value}
        access_token  = create_access_token(identity=member.account_id, additional_claims=additional_claims)
        refresh_token = create_refresh_token(identity=member.account_id, additional_claims=additional_claims)

        return MemberConverter.to_login_response_dto(member, access_token), refresh_token

    def logout(self, jti: str, exp: int) -> LogoutResponseDTO:
        """refresh token jti 블랙리스트 등록 (access token은 만료 시 자동 무효화)"""
        ttl = max(int(exp - datetime.now(timezone.utc).timestamp()), 0)
        redis_client.setex(f"{_BLACKLIST_PREFIX}{jti}", ttl, _BLACKLIST_VALUE)
        logger.info("logout — refresh jti blacklisted: %s (ttl=%ds)", jti, ttl)
        return MemberConverter.to_logout_response_dto()

    def recreate_token(self, identity: str, role: str, old_jti: str, old_exp: int) -> tuple:
        """Returns (new_access_token, new_refresh_token), 이전 refresh token rotation"""
        if redis_client.exists(f"{_BLACKLIST_PREFIX}{old_jti}"):
            raise ValueError("블랙리스트에 등록된 토큰입니다.")

        ttl = max(int(old_exp - datetime.now(timezone.utc).timestamp()), 0)
        redis_client.setex(f"{_BLACKLIST_PREFIX}{old_jti}", ttl, _BLACKLIST_VALUE)
        logger.info("token rotated — old refresh jti blacklisted: %s", old_jti)

        additional_claims = {"role": role}
        new_access_token  = create_access_token(identity=identity, additional_claims=additional_claims)
        new_refresh_token = create_refresh_token(identity=identity, additional_claims=additional_claims)
        return new_access_token, new_refresh_token
