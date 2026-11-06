"""Identifiers every module refers to. ``UserId`` lives here so modules need not import ``users`` for a type."""

from uuid import UUID

type UserId = UUID
