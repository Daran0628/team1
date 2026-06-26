from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def require_role(*roles: str):
    """JWT 'role' 클레임이 *roles* 중 하나인 사용자만 접근 허용.

    Usage::

        @app.route("/admin-only")
        @require_role("admin")
        def admin_page(): ...

        @app.route("/dashboard")
        @require_role("admin", "user")
        def dashboard(): ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            if get_jwt().get("role") not in roles:
                return jsonify({"msg": "접근 권한이 없습니다."}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
