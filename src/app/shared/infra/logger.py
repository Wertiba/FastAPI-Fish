"""Standard-library JSON logging with an explicit, privacy-safe event schema.

Code logs a known event name, never free text: ``logger.info("admin_created", extra={"user_id": ...})``.
Add new events to ``_EVENTS`` and their fields to ``_UUID_FIELDS`` / ``_FIELDS``.
"""

import json
import logging
import sys
import traceback
from contextvars import ContextVar
from typing import Any
from uuid import UUID

from app.shared.domain.time import TimeService
from app.shared.infra.config import LoggingConfig

# Set by the trace-id middleware; it only lets through ids matching a safe pattern.
log_trace_id: ContextVar[str | None] = ContextVar("log_trace_id", default=None)

# Messages are static: neither request data nor exception text belongs in logs.
_EVENTS = {
    "application_started": "API started",
    "application_stopped": "API stopped",
    "admin_created": "Admin user created from the environment",
    "http_request_completed": "HTTP request completed",
    "http_request_failed": "HTTP request failed",
    "unmapped_domain_error": "HTTP request raised an unmapped domain error",
    "application_error": "HTTP request raised an application error",
    # Background processes: worker, scheduler, bot.
    "process_started": "Process started",
    "process_stopped": "Process stopped",
    "outbox_relayed": "Outbox messages relayed to the broker",
    "outbox_relay_failed": "Outbox relay failed; will retry",
    "message_failed": "Consumer failed to handle a message; will retry",
    "message_dead_lettered": "Consumer gave up on a message; it is marked failed in the inbox",
    "job_completed": "Scheduled job completed",
    "job_failed": "Scheduled job failed",
    "job_skipped": "Scheduled job skipped: another instance holds its lock",
    # Outgoing messages; their content is never logged.
    "telegram_message_skipped": "Telegram is not configured; message not sent",
    "telegram_chat_unavailable": "Telegram chat is unavailable (bot blocked or chat deleted)",
    "push_skipped": "Push is not configured; notification not sent",
}
_UUID_FIELDS = frozenset({"user_id"})
_FIELDS = frozenset(
    {"http_method", "route", "status_code", "duration_ms", "process_name", "job", "topic", "handler", "count"}
)


def _uuid(value: object) -> str | None:
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


class JsonFormatter(logging.Formatter):
    def __init__(self, config: LoggingConfig) -> None:
        super().__init__()
        self.config = config

    def format(self, record: logging.LogRecord) -> str:
        event = record.msg if isinstance(record.msg, str) and record.name.startswith("app.") else None
        known_event = event in _EVENTS
        payload: dict[str, Any] = {
            "env": self.config.env,
            "system": self.config.system,
            "inst": self.config.inst,
            "@timestamp": TimeService.from_timestamp(record.created).isoformat(timespec="milliseconds"),
            "level": "WARN" if record.levelno == logging.WARNING else record.levelname,
            "logger": record.name,
            "event": event if known_event else "dependency_error",
            "message": _EVENTS[event] if event is not None and known_event else "Dependency reported a runtime error",
        }
        if trace_id := log_trace_id.get():
            payload["trace_id"] = trace_id
        if known_event:
            for field in _UUID_FIELDS:
                if value := _uuid(getattr(record, field, None)):
                    payload[field] = value
            for field in _FIELDS:
                value = getattr(record, field, None)
                if value is not None:
                    payload[field] = value
        if record.exc_info and record.exc_info[1] is not None:
            # Do not use formatException: exception messages, SQL parameters, source
            # lines and locals can all contain personal information or credentials.
            payload["error_type"] = type(record.exc_info[1]).__name__
            payload["error_stack"] = [
                {"module": frame.f_globals.get("__name__", ""), "function": frame.f_code.co_name, "line": line}
                for frame, line in traceback.walk_tb(record.exc_info[2])
            ]
        return json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


class EventFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        known_event = record.name.startswith("app.") and isinstance(record.msg, str) and record.msg in _EVENTS
        # Libraries can log URLs, credentials, SQL or payloads even at INFO. Only
        # preserve their errors, with a fixed message and sanitized exception data.
        return known_event or record.levelno >= logging.ERROR


class Logger:
    """Configure once at application bootstrap; call logging.getLogger(__name__) elsewhere."""

    def __init__(self, console_config: LoggingConfig) -> None:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter(console_config))
        handler.addFilter(EventFilter())
        logging.basicConfig(handlers=[handler], level=console_config.level, force=True)
        # Remove library-owned console handlers so every runtime line uses the
        # same formatter. In particular, Uvicorn must not log raw access URLs.
        for item in logging.root.manager.loggerDict.values():
            if isinstance(item, logging.Logger):
                item.handlers.clear()
                item.propagate = True
                item.disabled = False
                item.setLevel(logging.NOTSET)
        logging.getLogger("uvicorn.access").disabled = True
