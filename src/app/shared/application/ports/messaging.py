from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, kw_only=True)
class TelegramButton:
    text: str
    callback_data: str


class TelegramSender(Protocol):
    """Outgoing Telegram messages. Any process may send; the ``bot`` process is only for incoming updates."""

    async def send_message(self, chat_id: int, text: str, buttons: Sequence[Sequence[TelegramButton]] = ()) -> None: ...


@dataclass(frozen=True, kw_only=True)
class PushMessage:
    title: str
    body: str
    data: Mapping[str, str] = field(default_factory=dict)


class PushSender(Protocol):
    """Push notifications to mobile apps (FCM; iOS too, through FCM)."""

    async def send(self, device_token: str, message: PushMessage) -> bool:
        """``False`` when the token is no longer registered: the caller should forget the device."""
        ...
