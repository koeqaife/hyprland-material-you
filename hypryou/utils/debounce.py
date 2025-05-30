import typing as t
import asyncio
import functools
from repository import glib


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


def sync_debounce(
    delay: int,
    min_n_times: int = 0,
    immediate: bool = False
) -> t.Callable[..., t.Any]:
    def decorator(func: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
        n_times = 0
        timeout_id: int | None = None
        last_args: tuple[t.Any, ...] = ()
        last_kwargs: dict[str, t.Any] = {}

        def call_func() -> bool:
            nonlocal timeout_id, n_times
            if n_times > min_n_times:
                func(*last_args, **last_kwargs)
            n_times = 0
            timeout_id = None
            return False

        def wrapper(*args: t.Any, **kwargs: t.Any) -> None:
            nonlocal timeout_id, last_args, last_kwargs, n_times

            last_args = args
            last_kwargs = kwargs

            if timeout_id is not None:
                glib.source_remove(timeout_id)

            if not immediate or n_times < min_n_times:
                n_times += 1
                timeout_id = glib.timeout_add(
                    delay,
                    call_func
                )
            else:
                n_times = 0
                timeout_id = None
                func(*last_args, **last_kwargs)

        return functools.wraps(func)(wrapper)

    return decorator
