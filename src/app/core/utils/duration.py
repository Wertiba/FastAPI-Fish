import re

_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
_PATTERN = re.compile(r"^(\d+)([smhd])$")


def parse_duration_seconds(value: str) -> int:
    match = _PATTERN.match(value.strip())
    if not match:
        raise ValueError(f"Invalid duration format: {value!r} (expected e.g. '15m', '30d')")
    amount, unit = match.groups()
    return int(amount) * _UNIT_SECONDS[unit]
