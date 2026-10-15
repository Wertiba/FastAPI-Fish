"""Реестр модулей. Новый домен = новая строка здесь (``scripts/new_module.py`` добавит сам)."""

from app.modules.auth.module import auth_module
from app.modules.users.module import users_module
from app.shared.module import Module

MODULES: tuple[Module, ...] = (
    auth_module,
    users_module,
)
