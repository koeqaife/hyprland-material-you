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
    def __init__(self, no_idle_pending: bool = False) -> None:
        self._signals: dict[str, dict[int, Wrapper]] = {}
        self._handler_signals: dict[int, str] = {}
        self._blocked: set[str] = set()
        self._lock = threading.RLock()
        self._pending_idle: set[str] = set()
        self._no_idle_pending = no_idle_pending

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
            base_id = max(self._handler_signals.keys(), default=0) + 1
            handler_id = base_id + priority * 0x10000
            callbacks[handler_id] = wrapper
            self._handler_signals[handler_id] = signal_name
            return handler_id

    def unwatch_fast(self, signal_name: str, handler_id: int) -> bool:
        with self._lock:
            callbacks = self._signals.get(signal_name)
            if not callbacks or handler_id not in callbacks:
                return False
            del callbacks[handler_id]
            del self._handler_signals[handler_id]
            return True

    def unwatch(self, handler_id: int) -> bool:
        with self._lock:
            signal_name = self._handler_signals[handler_id]
            callbacks = self._signals.get(signal_name)
            if not callbacks or handler_id not in callbacks:
                return False
            del callbacks[handler_id]
            del self._handler_signals[handler_id]
            return True

    def notify_sync(self, signal_name: str, *args: t.Any) -> None:
        with self._lock:
            if signal_name in self._blocked:
                return

            signal_callbacks = self._signals.get(signal_name)
            if signal_callbacks is None:
                return

            to_remove: list[int] = []
            for handler_id in sorted(signal_callbacks):
                cb = self._signals[signal_name][handler_id]
                try:
                    result = cb(*args)
                    if result not in (None, True):
                        to_remove.append(handler_id)
                except Exception as e:
                    logger.error(
                        "Error while calling callback: %s",
                        e, exc_info=e
                    )
                    to_remove.append(handler_id)

            for handler_id in to_remove:
                del signal_callbacks[handler_id]
                self._handler_signals.pop(handler_id, None)

    def _idle_notify(self, signal_name: str, *args: t.Any) -> bool:
        if not self._no_idle_pending:
            with self._lock:
                self._pending_idle.discard(signal_name)
        self.notify_sync(signal_name, *args)
        return False

    def notify(
        self,
        signal_name: str,
        *args: t.Any
    ) -> None:
        if not self._no_idle_pending:
            with self._lock:
                if signal_name in self._pending_idle:
                    return
                self._pending_idle.add(signal_name)
        glib.idle_add(self._idle_notify, signal_name, *args)

    def block(self, signal_name: str) -> None:
        with self._lock:
            self._blocked.add(signal_name)

    def unblock(self, signal_name: str) -> None:
        with self._lock:
            self._blocked.discard(signal_name)

    def handlers(self, signal_name: str) -> list[int]:
        with self._lock:
            return list(self._signals.get(signal_name, ()))

    def clear(self, signal_name: str) -> None:
        with self._lock:
            callbacks = self._signals.pop(signal_name, {})
            for handler_id in callbacks:
                self._handler_signals.pop(handler_id, None)


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
