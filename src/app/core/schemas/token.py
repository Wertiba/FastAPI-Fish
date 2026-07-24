from app.core.config import settings
from app.core.schemas.base import PyModel


class Token(PyModel):
    accessToken: str
    expiresIn: int = settings.token.access_token.lifetime_seconds
