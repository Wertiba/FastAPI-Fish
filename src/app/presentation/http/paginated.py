from pydantic import BaseModel


class PaginationParams(BaseModel):
    page: int = 0
    size: int = 20


# The name gives the OpenAPI component ``Page_UserReadResponse_``.
class Page[T](BaseModel):
    items: list[T]
    page: int
    size: int
    total: int
