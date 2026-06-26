from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash

# TODO: DB 연동으로 교체 예정 (현재 mockup)
_USERS = [
    {
        "id": 1,
        "email": "admin@example.com",
        "password_hash": generate_password_hash("admin1234"),
        "name": "관리자",
        "role": "admin",
    },
    {
        "id": 2,
        "email": "user@example.com",
        "password_hash": generate_password_hash("user1234"),
        "name": "일반사용자",
        "role": "user",
    },
]

_USER_BY_EMAIL: dict = {u["email"]: u for u in _USERS}


def find_user_by_email(email: str) -> Optional[dict]:
    return _USER_BY_EMAIL.get(email)


def verify_password(user: dict, plain_password: str) -> bool:
    return check_password_hash(user["password_hash"], plain_password)
