from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthConfig:
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_ttl_seconds: int = 15 * 60
    refresh_ttl_seconds: int = 30 * 24 * 3600
    cookie_secure: bool = True
