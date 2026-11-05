from app.presentation.http.schemas.base import PyModel


class AccessTokenResponse(PyModel):
    accessToken: str
    expiresIn: int
