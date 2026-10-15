from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Pagination:
    page: int = 0
    size: int = 20

    @property
    def offset(self) -> int:
        return self.page * self.size

    @property
    def limit(self) -> int:
        return self.size


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
