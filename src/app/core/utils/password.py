import re


def check_len_password(password: str) -> str:
    if not (8 <= len(password) <= 72):
        raise ValueError("Password must be between 8 and 72 characters")

    if not re.search(r"[A-Za-z]", password):
        raise ValueError("Password must contain at least one letter")

    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")

    return password
