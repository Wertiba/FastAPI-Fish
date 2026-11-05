from dishka import Provider, Scope, provide_all

from app.application.auth.interactors import LoginUser, Logout, RefreshTokens, RegisterUser, VerifyAccessToken


class AuthProvider(Provider):
    scope = Scope.REQUEST
    interactors = provide_all(RegisterUser, LoginUser, RefreshTokens, Logout, VerifyAccessToken)
