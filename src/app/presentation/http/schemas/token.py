from app.presentation.http.schemas.base import PyModel


class AccessTokenResponse(PyModel):
    access_token: str
    expires_in: int
