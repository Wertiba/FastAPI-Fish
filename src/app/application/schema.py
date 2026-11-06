from pydantic import BaseModel, ConfigDict, field_validator
from pydantic.alias_generators import to_camel


class PyModel(BaseModel):
    """Fields are snake_case like the entities; JSON and OpenAPI see their camelCase aliases.

    So ``Entity(**data.model_dump())`` works inside, while the API contract stays camelCase.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        from_attributes=True,
        allow_inf_nan=False,
    )

    @field_validator("*")
    @classmethod
    def reject_nul(cls, value: object) -> object:
        # Postgres text cannot hold NUL, so such input would fail in the database with a 500.
        texts = value if isinstance(value, list) else [value]
        if any(isinstance(text, str) and "\x00" in text for text in texts):
            raise ValueError("text must not contain NUL characters")
        return value
