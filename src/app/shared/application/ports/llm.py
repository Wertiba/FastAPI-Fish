from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol


@dataclass(frozen=True, kw_only=True)
class LlmMessage:
    role: Literal["system", "user", "assistant"]
    content: str


class LlmClient(Protocol):
    """A chat model (Ollama). Slow and non-deterministic: callers validate what it returns.

    Both methods raise ``ServiceUnavailableError`` when the model is disabled, down or too slow.
    """

    async def complete(self, messages: list[LlmMessage], *, json_schema: Mapping[str, Any] | None = None) -> str:
        """The whole answer. With ``json_schema`` the model must answer JSON matching it (structured output)."""
        ...

    def stream(self, messages: list[LlmMessage]) -> AsyncIterator[str]:
        """The answer in chunks as they are generated, for SSE or editing a Telegram message."""
        ...
