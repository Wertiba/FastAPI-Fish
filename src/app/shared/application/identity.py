"""Кто выполняет запрос.

Контракт живёт в shared kernel, реализация — в модуле ``auth``
(``BearerIdentityProvider``). Любой модуль получает текущего пользователя через
``IdentityProvider`` и ничего не знает о JWT, заголовках и куках.
"""

from typing import Protocol

from app.shared.domain.identity import Identity


class IdentityProvider(Protocol):
    async def get_identity(self) -> Identity:
        """Текущий пользователь; бросает ``AuthenticationError``, если его нет."""
        ...
