from dataclasses import dataclass


@dataclass
class Pagination:
    page: int = 0
    size: int = 20

    @property
    def offset(self) -> int:
        return self.page * self.size

    @property
    def limit(self) -> int:
        return self.size


@dataclass
class Page[T]:
    items: list[T]
    page: int
    size: int
    total: int

    @staticmethod
    def build[Item](items: list[Item], total: int, pagination: Pagination) -> "Page[Item]":
        return Page(items=items, total=total, page=pagination.page, size=pagination.size)
