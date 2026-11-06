"""Bot commands every module shares; module handlers live in ``modules/<m>/presentation/telegram.py``."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

HELP = "Команды:\n/start — начать\n/help — эта справка"


def build_router() -> Router:
    """A new router per dispatcher: aiogram attaches a router to one parent only."""
    router = Router(name="common")

    @router.message(CommandStart())
    async def start(message: Message) -> None:
        await message.answer("Привет! " + HELP)

    @router.message(Command("help"))
    async def help_(message: Message) -> None:
        await message.answer(HELP)

    @router.message(F.text)
    async def unknown(message: Message) -> None:
        await message.answer("Не понял. " + HELP)

    return router
