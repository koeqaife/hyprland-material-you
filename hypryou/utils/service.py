import typing as t
import types
import weakref
import threading
from utils.logger import logger
from repository import glib

# I don't wanna use GObject for signals in objects so I decided to do this code

Callback = t.Callable[..., None]
Wrapper = t.Callable[..., bool | None]


class Signals:
    def __init__(self) -> None:
        self._signals: dict[str, dict[int, Wrapper]] = {}
        self._blocked: set[str] = set()
        self._lock = threading.RLock()

    def watch(
        self,
        signal_name: str,
        callback: Callback,
        *,
        once: bool = False,
        priority: int = 0
    ) -> int:
        with self._lock:
            if isinstance(callback, types.MethodType):
                ref = weakref.WeakMethod(callback)

                def wrapper(*args: t.Any) -> bool | None:
                    func = ref()
                    if func is not None:
                        func(*args)
                        return True
                    return False
            else:
                wrapper = callback

            if once:
                original = wrapper

                def one_shot(*a: t.Any) -> bool:
                    original(*a)
                    return False

                wrapper = one_shot

            callbacks = self._signals.setdefault(signal_name, {})
            base_id = max(callbacks.keys(), default=0) + 1
            handler_id = base_id + priority * 0x10000
            callbacks[handler_id] = wrapper
            return handler_id

    def unwatch(self, signal_name: str, handler_id: int) -> bool:
        with self._lock:
            callbacks = self._signals.get(signal_name)
            if not callbacks or handler_id not in callbacks:
                return False
            del callbacks[handler_id]
            return True

    def notify_sync(self, signal_name: str, *args: t.Any) -> None:
        with self._lock:
            if signal_name in self._blocked:
                return

            signal_callbacks = self._signals.get(signal_name)
            if signal_callbacks is None:
                return

            for handler_id in sorted(signal_callbacks):
                cb = self._signals[signal_name][handler_id]
                try:
                    result = cb(*args)
                    if result not in (None, True):
                        del self._signals[signal_name][handler_id]
                except Exception as e:
                    logger.error(
                        "Error while calling callback: %s",
                        e, exc_info=e
                    )
                    del self._signals[signal_name][handler_id]

    def notify(self, signal_name: str, *args: t.Any) -> None:
        glib.idle_add(self.notify_sync, signal_name, *args)

    def block(self, signal_name: str) -> None:
        with self._lock:
            self._blocked.add(signal_name)

    def unblock(self, signal_name: str) -> None:
        with self._lock:
            self._blocked.discard(signal_name)

    def handlers(self, signal_name: str) -> list[int]:
        with self._lock:
            return list(self._signals.get(signal_name, {}).keys())

    def clear(self, signal_name: str) -> None:
        with self._lock:
            self._signals.pop(signal_name, None)


class Service:
    def __init__(self) -> None:
        ...

    def app_init(self) -> None:
        ...

    def start(self) -> None:
        ...

    def on_close(self) -> None:
        ...


class AsyncService:
    def __init__(self) -> None:
        ...

    async def app_init(self) -> None:
        ...

    async def start(self) -> None:
        ...

    def on_close(self) -> None:
        ...
