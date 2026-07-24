import logging
import os
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from app.core.config import settings
from app.core.utils import Singleton


class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_back and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


class Logger(Singleton):
    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO)
        logger.remove()

        logger.add(
            sys.stdout,
            format=settings.logging.console.FORMAT,
            level=settings.logging.console.LEVEL,
            enqueue=settings.logging.console.ENQUEUE,
            backtrace=settings.logging.console.BACKTRACE,
            diagnose=settings.logging.console.DIAGNOSE,
        )

        logger.add(
            os.path.join(Path(__file__).parent.parent.parent, settings.logging.file.path),
            rotation=settings.logging.file.rotation,
            retention=settings.logging.file.retention,
            compression=settings.logging.file.compression,
            level=settings.logging.file.level,
            enqueue=settings.logging.file.enqueue,
            backtrace=settings.logging.file.backtrace,
            diagnose=settings.logging.file.diagnose,
        )

        loggers = ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "asyncio", "starlette")
        for logger_name in loggers:
            logging_logger = logging.getLogger(logger_name)
            logging_logger.handlers = []
            logging_logger.propagate = True

        self._initialized = True

    @staticmethod
    def get_logger() -> Any:
        return logger
