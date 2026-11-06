from app.application.schema import PyModel


class AccessTokenResponse(PyModel):
    access_token: str
    expires_in: int
