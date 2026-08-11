import pytest

from app.core.utils.duration import parse_duration_seconds


def test_parses_minutes():
    assert parse_duration_seconds("15m") == 900


def test_parses_days():
    assert parse_duration_seconds("30d") == 30 * 86400


def test_parses_seconds_and_hours():
    assert parse_duration_seconds("45s") == 45
    assert parse_duration_seconds("2h") == 7200


def test_rejects_bad_format():
    with pytest.raises(ValueError):
        parse_duration_seconds("15")
    with pytest.raises(ValueError):
        parse_duration_seconds("15x")
