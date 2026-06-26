import os

import redis as redis_lib

_r = redis_lib.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True,
)


def add_token_to_blacklist(jti: str, expires_in: int) -> None:
    _r.setex(f"blacklist:{jti}", expires_in, "revoked")


def is_token_blacklisted(jti: str) -> bool:
    return _r.exists(f"blacklist:{jti}") == 1
