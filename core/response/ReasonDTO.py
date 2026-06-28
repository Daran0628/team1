from dataclasses import dataclass
from http import HTTPStatus
from typing import Optional


@dataclass
class ReasonDTO:
    is_success: bool
    code: str
    message: str
    http_status: Optional[HTTPStatus] = None
