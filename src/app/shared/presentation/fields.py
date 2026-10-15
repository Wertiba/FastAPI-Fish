"""Переиспользуемые типы полей для request-схем любых модулей."""

import re
from typing import Annotated

from pydantic import AfterValidator, EmailStr, Field


def _check_password(value: str) -> str:
    if not 8 <= len(value) <= 72:
        raise ValueError("Password must be between 8 and 72 characters")
    if not re.search(r"[A-Za-z]", value):
        raise ValueError("Password must contain at least one letter")
    if not re.search(r"\d", value):
        raise ValueError("Password must contain at least one digit")
    return value


Email = Annotated[EmailStr, Field(max_length=254)]
Password = Annotated[str, AfterValidator(_check_password)]
FullName = Annotated[str, Field(pattern=r"^[а-яА-Яa-zA-Z0-9 _-]{2,200}$")]
