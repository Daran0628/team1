from functools import wraps

from core.response.ApiResponse import ApiResponse
from core.response.ErrorStatus import ErrorStatus
from flask_jwt_extended import get_jwt



def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            if claims.get("role") not in roles:
                return ApiResponse.on_failure(ErrorStatus._FORBIDDEN)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
