"""One image, several processes: ``python -m app.run <process>``.

    api        FastAPI (site + mobile app); the default
    worker     outbox relay + consumers (Kafka or local)
    scheduler  periodic jobs
    bot        Telegram long polling

Each process imports only what it runs, so ``bot`` does not load uvicorn and ``api`` does not touch Kafka.
"""

import argparse
import asyncio
import contextlib
import signal
from collections.abc import Callable, Coroutine
from importlib import import_module
from typing import Any

PROCESSES = ("api", "worker", "scheduler", "bot")


def run_api() -> None:
    import uvicorn

    from app.entrypoints.api import app
    from app.shared.infra.config import RunConfig

    config = app.state.dishka_container.get_sync(RunConfig)
    # Access lines come from ObservabilityMiddleware (with trace id), so uvicorn's own are off.
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        access_log=False,
        log_config=None,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


async def _until_stopped(main: Callable[[], Coroutine[Any, Any, None]]) -> None:
    """SIGTERM (docker stop) cancels the main task, so the process closes its connections on the way out."""
    task = asyncio.current_task()
    if task is None:
        raise RuntimeError("must run inside a task")
    with contextlib.suppress(NotImplementedError):  # no signal handlers in the Windows event loop
        asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, task.cancel)
    await main()


def run_async(process: str) -> None:
    main: Callable[[], Coroutine[Any, Any, None]] = import_module(f"app.entrypoints.{process}").main
    with contextlib.suppress(KeyboardInterrupt, asyncio.CancelledError):
        asyncio.run(_until_stopped(main))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m app.run", description=__doc__.split("\n\n")[0])
    parser.add_argument("process", nargs="?", default="api", choices=PROCESSES)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    process: str = parse_args(argv).process
    if process == "api":
        run_api()
    else:
        run_async(process)


if __name__ == "__main__":
    main()
