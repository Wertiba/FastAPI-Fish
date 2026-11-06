"""``bot`` process: incoming Telegram updates (commands, buttons, text) via long polling.

Handlers live in modules (``Module.bot_router``) and get use cases with ``FromDishka[...]``, exactly like
HTTP endpoints; each update is one DI request scope. Outgoing messages need no bot process: any process
sends through ``TelegramSender``. Run exactly one replica: Telegram allows a single polling client.
"""

import logging

from aiogram import Bot, Dispatcher
from dishka.integrations.aiogram import AiogramProvider, setup_dishka

from app.bootstrap import MODULES, build_container
from app.shared.infra.config import TelegramConfig
from app.shared.infra.logger import Logger
from app.shared.presentation.telegram import build_router

logger = logging.getLogger(__name__)


def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    for module in MODULES:
        if module.bot_router is not None:
            dispatcher.include_router(module.bot_router)
    # Last: its catch-all reply must not shadow the modules' handlers.
    dispatcher.include_router(build_router())
    return dispatcher


async def main() -> None:
    container = build_container(AiogramProvider())
    await container.get(Logger)
    config = await container.get(TelegramConfig)
    if not config.bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set")
    bot = Bot(config.bot_token)
    dispatcher = build_dispatcher()
    setup_dishka(container=container, router=dispatcher, auto_inject=True)
    logger.info("process_started", extra={"process_name": "bot"})
    try:
        await dispatcher.start_polling(bot, handle_signals=False)
    finally:
        await bot.session.close()
        await container.close()
        logger.info("process_stopped", extra={"process_name": "bot"})
