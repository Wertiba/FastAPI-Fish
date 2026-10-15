"""loguru: цветная консоль + ротируемый файл, trace-id в каждой строке.

Стандартный ``logging`` (uvicorn, sqlalchemy, …) перенаправляется в loguru.
"""

import inspect
import logging
import sys
from pathlib import Path
from types import FrameType
from typing import TYPE_CHECKING

from loguru import logger

from app.shared.presentation.request_context import get_trace_id

if TYPE_CHECKING:
    from loguru import Record

CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
    "<magenta>{extra[trace_id]}</magenta> | <cyan>{name}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)
FILE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[trace_id]} | {name}:{line} | {message}"


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame: FrameType | None = inspect.currentframe()
        depth = 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _add_trace_id(record: "Record") -> None:
    record["extra"]["trace_id"] = get_trace_id() or "-"


def setup_logging(level: str = "INFO", log_file: str = "") -> None:
    logger.remove()
    logger.configure(patcher=_add_trace_id)
    logger.add(sys.stdout, level=level, format=CONSOLE_FORMAT, backtrace=True, diagnose=False)
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            level=level,
            format=FILE_FORMAT,
            rotation="10 MB",
            retention="10 days",
            compression="zip",
            enqueue=True,
            diagnose=False,
        )

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        std_logger = logging.getLogger(name)
        std_logger.handlers = []
        std_logger.propagate = True
