import dataclasses
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from flask import jsonify

from core.response.ErrorStatus import ErrorStatus
from core.response.SuccessStatus import SuccessStatus


def _serialize(obj: Any) -> Any:
    """dataclass / Enum / datetime 을 JSON 직렬화 가능한 형태로 변환."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _serialize(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, list):
        return [_serialize(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


class ApiResponse:

    @staticmethod
    def on_success(status: SuccessStatus, result: Optional[Any] = None):
        """성공 응답 반환. (flask response, http_status_code) 튜플."""
        body = {
            "isSuccess": True,
            "code": status.code,
            "message": status.message,
            "result": _serialize(result),
        }
        return jsonify(body), status.http_status.value

    @staticmethod
    def on_failure(status: ErrorStatus, result: Optional[Any] = None):
        """실패 응답 반환. (flask response, http_status_code) 튜플."""
        body = {
            "isSuccess": False,
            "code": status.code,
            "message": status.message,
            "result": _serialize(result),
        }
        return jsonify(body), status.http_status.value
