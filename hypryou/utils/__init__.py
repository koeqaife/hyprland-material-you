import utils.cliphist as cliphist
import utils.ref as ref
import utils.widget as widget
import utils.format as format
import utils.downloader as downloader
import utils.colors as colors

from utils.ref import Ref
from utils.logger import setup_logger
from utils.styles import (
    apply_css,
    reload_css,
    compile_scss,
    toggle_css_class
)
from utils.format import (
    get_formatted_date,
    get_formatted_time,
    escape_markup,
    get_full_date
)

import typing as t
import asyncio
import functools

__all__ = [
    "cliphist",
    "widget",
    "Ref",
    "ref",
    "setup_logger",
    "apply_css",
    "reload_css",
    "compile_scss",
    "get_formatted_date",
    "get_formatted_time",
    "get_full_date",
    "toggle_css_class",
    "format",
    "debounce",
    "downloader",
    "escape_markup",
    "colors"
]


def debounce(delay: float) -> t.Callable[..., t.Any]:
    def decorator(func: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
        task: asyncio.Task[None] | None = None

        @functools.wraps(func)
        async def wrapper(*args: t.Any, **kwargs: t.Any) -> None:
            nonlocal task

            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            async def delayed_call() -> None:
                await asyncio.sleep(delay)
                await func(*args, **kwargs)

            task = asyncio.create_task(delayed_call())

        return wrapper

    return decorator
