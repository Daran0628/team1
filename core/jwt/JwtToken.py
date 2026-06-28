from dataclasses import dataclass


@dataclass
class JwtToken:
    grant_type: str
    access_token: str
    refresh_token: str
