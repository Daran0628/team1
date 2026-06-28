import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class LoginRequestDTO:
    account_id: str
    password: str

    _ACCOUNT_ID_PATTERN = re.compile(r'^(?=.*[a-z])[a-zA-Z\d.]{3,15}$')
    _PASSWORD_PATTERN = re.compile(r'^(?=.*[a-z])(?=.*\d)[a-zA-Z\d]{9,16}$')

    def __post_init__(self):
        if not self.account_id or not self.account_id.strip():
            raise ValueError("사원명은 필수 입력 값 입니다.")
        if not self._ACCOUNT_ID_PATTERN.fullmatch(self.account_id):
            raise ValueError(
                "영문 소문자와 숫자가 적어도 1개 이상씩 포함된 3자 ~ 15자의 사원명을 입력해주세요."
            )

        if not self.password or not self.password.strip():
            raise ValueError("비밀번호는 필수 입력 값 입니다.")
        if not self._PASSWORD_PATTERN.fullmatch(self.password):
            raise ValueError(
                "영문 소문자와 숫자가 적어도 1개 이상씩 포함된 9자 ~ 16자의 비밀번호를 입력해주세요."
            )


@dataclass
class LogoutRequestDTO:
    account_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
