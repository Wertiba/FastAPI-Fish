from typing import Generic

from pydantic import BaseModel, Field

from app.core.custom_types import T


class PaginationParams(BaseModel):
    page: int = Field(1, ge=0, description="Page number")
    size: int = Field(10, ge=1, le=1000, description="Page size")

    @property
    def offset(self) -> int:
        return self.page * self.size

    @property
    def limit(self) -> int:
        return self.size


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    size: int
    total: int

    @staticmethod
    def build(items: list[T], total: int, pagination: PaginationParams) -> "Page[T]":
        if len(items) > pagination.size:
            raise ValueError("items length exceeds pagination.size")

        return Page[T](items=items, page=pagination.page, size=pagination.size, total=total)
