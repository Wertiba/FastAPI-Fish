from app.core.schemas.base import PyModel


class Token(PyModel):
    accessToken: str
    expiresIn: int


class AccessTokenResponse(PyModel):
    accessToken: str
    expiresIn: int
