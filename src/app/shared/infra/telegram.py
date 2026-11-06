"""Outgoing Telegram messages through the Bot API; only logged when ``TELEGRAM_BOT_TOKEN`` is empty."""

import logging
from collections.abc import AsyncIterator, Sequence

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dishka import Provider, Scope, provide

from app.shared.application.exceptions import ServiceUnavailableError
from app.shared.application.ports.messaging import TelegramButton, TelegramSender
from app.shared.infra.config import TelegramConfig

logger = logging.getLogger(__name__)


class BotApiTelegramSender(TelegramSender):
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_message(self, chat_id: int, text: str, buttons: Sequence[Sequence[TelegramButton]] = ()) -> None:
        markup = None
        if buttons:
            markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=button.text, callback_data=button.callback_data) for button in row]
                    for row in buttons
                ]
            )
        try:
            await self._bot.send_message(chat_id, text, reply_markup=markup)
        except TelegramForbiddenError:
            # The user blocked the bot: nothing to retry; the caller may unlink the chat.
            logger.warning("telegram_chat_unavailable")
        except TelegramAPIError as exc:
            raise ServiceUnavailableError("Telegram request failed") from exc


class LogTelegramSender(TelegramSender):
    """Development: logs that a message would be sent (never its text: it can hold personal data)."""

    async def send_message(self, chat_id: int, text: str, buttons: Sequence[Sequence[TelegramButton]] = ()) -> None:
        logger.info("telegram_message_skipped")


class TelegramProvider(Provider):
    scope = Scope.APP

    @provide
    async def sender(self, config: TelegramConfig) -> AsyncIterator[TelegramSender]:
        if not config.bot_token:
            yield LogTelegramSender()
            return
        bot = Bot(config.bot_token)
        try:
            yield BotApiTelegramSender(bot)
        finally:
            await bot.session.close()
