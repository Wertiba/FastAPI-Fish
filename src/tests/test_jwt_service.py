import jwt
import pytest

from app.core.exceptions.user_exs import InvalidCredentialsError
from app.services.jwt_service import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE, JWTService


@pytest.fixture
def jwt_service():
    return JWTService()


def test_access_token_has_expected_claims(jwt_service):
    token = jwt_service.create_access_token("user-123")
    payload = jwt.decode(token, jwt_service.secret_key, algorithms=[jwt_service.algorithm])

    assert payload["sub"] == "user-123"
    assert payload["type"] == ACCESS_TOKEN_TYPE
    assert "jti" in payload
    assert "iat" in payload
    assert "exp" in payload


def test_refresh_token_has_refresh_type(jwt_service):
    token = jwt_service.create_refresh_token("user-123")
    payload = jwt.decode(token, jwt_service.secret_key, algorithms=[jwt_service.algorithm])
    assert payload["type"] == REFRESH_TOKEN_TYPE


def test_decode_token_rejects_wrong_type(jwt_service):
    access_token = jwt_service.create_access_token("user-123")
    with pytest.raises(InvalidCredentialsError):
        jwt_service.decode_token(access_token, expected_type=REFRESH_TOKEN_TYPE)


def test_decode_token_rejects_garbage(jwt_service):
    with pytest.raises(InvalidCredentialsError):
        jwt_service.decode_token("not-a-real-token", expected_type=ACCESS_TOKEN_TYPE)


def test_decode_token_accepts_matching_type(jwt_service):
    token = jwt_service.create_access_token("user-123")
    payload = jwt_service.decode_token(token, expected_type=ACCESS_TOKEN_TYPE)
    assert payload["sub"] == "user-123"


def test_hash_token_is_deterministic_sha256():
    h1 = JWTService.hash_token("raw-token-value")
    h2 = JWTService.hash_token("raw-token-value")
    assert h1 == h2
    assert len(h1) == 64


def test_password_hash_roundtrip(jwt_service):
    hashed = jwt_service.get_password_hash("s3cret123")
    assert jwt_service.verify_password("s3cret123", hashed)
    assert not jwt_service.verify_password("wrong", hashed)


def test_expire_seconds_come_from_env_vars(jwt_service):
    assert jwt_service.access_expire_seconds == 15 * 60
    assert jwt_service.refresh_expire_seconds == 30 * 86400
