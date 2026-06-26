import os

# 'redis/' 폴더가 PyPI redis 패키지와 동명이라 __init__.py를 두지 않음.
# app.py에서 sys.path에 redis/ 디렉토리를 추가해 이 파일을 직접 임포트함.
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
