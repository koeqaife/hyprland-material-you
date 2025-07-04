import asyncio
import typing as t
from collections.abc import MutableSequence, MutableSet
from utils.logger import logger
from utils.service import Signals

__all__ = [
    "Ref"
]

T = t.TypeVar("T")
U = t.TypeVar("U")
L = t.TypeVar("L")
K = t.TypeVar("K")
V = t.TypeVar("V")


class ReactiveList(MutableSequence[L], t.Generic[L]):
    def __init__(self, data: list[L], ref: "Ref[list[L]]"):
        self._data = data
        self._ref = ref

    @t.overload
    def __getitem__(self, i: int) -> L:
        ...

    @t.overload
    def __getitem__(self, i: slice) -> "ReactiveList[L]":
        ...

    def __getitem__(self, i: int | slice) -> L | "ReactiveList[L]":
        if isinstance(i, slice):
            slice_result = self._data[i]
            return ReactiveList(slice_result, self._ref)
        else:
            result = self._data[i]
            return result

    @t.overload
    def __setitem__(self, index: int, value: L) -> None:
        ...

    @t.overload
    def __setitem__(self, index: slice, values: t.Iterable[L]) -> None:
        ...

    def __setitem__(
        self,
        index: int | slice,
        value: L | t.Iterable[L]
    ) -> None:
        if isinstance(index, int):
            if t.TYPE_CHECKING:
                value = t.cast(L, value)
            self._check_type(value)
            self._data[index] = value
        else:
            if t.TYPE_CHECKING:
                value = t.cast(t.Iterable[L], value)
            for v in value:
                self._check_type(v)
            self._data[index] = value

        if self._ref.is_ready:
            self._ref._trigger_watchers()

    def _check_type(self, value: L) -> None:
        if self._ref.types and not isinstance(value, self._ref.types):
            raise TypeError(
                f"Types do not match {repr(value)}: " +
                f"{type(value)} not in {self._ref.types}"
            )

    @t.overload
    def __delitem__(self, index: int) -> None:
        ...

    @t.overload
    def __delitem__(self, index: slice) -> None:
        ...

    def __delitem__(self, index: int | slice) -> None:
        del self._data[index]
        if self._ref.is_ready:
            self._ref._trigger_watchers()

    def clear(self) -> None:
        self._data.clear()
        if self._ref.is_ready:
            self._ref._trigger_watchers()

    def pop(self, index: int = -1) -> L:
        value = self._data.pop(index)
        if self._ref.is_ready:
            self._ref._trigger_watchers()
        return value

    def insert(self, i: int, value: L) -> None:
        self._check_type(value)
        self._data.insert(i, value)

        if self._ref.is_ready:
            self._ref._trigger_watchers()

    def append(self, value: L) -> None:
        self._check_type(value)
        self._data.append(value)

        if self._ref.is_ready:
            self._ref._trigger_watchers()

    def __contains__(self, value: object) -> bool:
        return value in self._data

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return repr(self._data)


class ReactiveSet(MutableSet[L], t.Generic[L]):
    def __init__(self, data: set[L], ref: "Ref[set[L]]"):
        self._data = data
        self._ref = ref

    def _check_type(self, value: L) -> None:
        if self._ref.types and not isinstance(value, self._ref.types):
            raise TypeError(
                f"Types do not match {repr(value)}: " +
                f"{type(value)} not in {self._ref.types}"
            )

    def __contains__(self, item: object) -> bool:
        return item in self._data

    def __iter__(self) -> t.Iterator[L]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def add(self, value: L) -> None:
        if value not in self._data:
            self._check_type(value)
            self._data.add(value)

            if self._ref.is_ready:
                self._ref._trigger_watchers()

    def discard(self, value: L) -> None:
        if value in self._data:
            self._data.discard(value)

            if self._ref.is_ready:
                self._ref._trigger_watchers()

    def remove(self, value: L) -> None:
        if value not in self._data:
            raise KeyError(value)
        self._data.remove(value)

        if self._ref.is_ready:
            self._ref._trigger_watchers()

    def __repr__(self) -> str:
        return repr(self._data)


class ReactiveDict(dict[K, V], t.Generic[K, V]):
    def __init__(self, data: dict[K, V], parent_ref: 'Ref[t.Any]') -> None:
        super().__init__()
        self._ref = parent_ref
        self._initialized = False
        for k, v in data.items():
            self[k] = v
        self._initialized = True

    def __setitem__(self, key: K, value: V) -> None:
        wrapped_value = self._ref._wrap_if_mutable(value)
        super().__setitem__(key, wrapped_value)

        if self._ref.is_ready and self._initialized:
            self._ref._trigger_watchers()

    def __delitem__(self, key: K) -> None:
        super().__delitem__(key)
        if self._ref.is_ready:
            self._ref._trigger_watchers()

    def clear(self) -> None:
        super().clear()
        if self._ref.is_ready:
            self._ref._trigger_watchers()

    @t.overload
    def pop(self, key: K) -> V: ...

    @t.overload
    def pop(self, key: K, default: T) -> t.Union[V, T]: ...

    def pop(self, key: K, default: t.Any = t.NoReturn) -> t.Any:
        if default is t.NoReturn:
            result = super().pop(key)
        else:
            result = super().pop(key, default)
        if self._ref.is_ready:
            self._ref._trigger_watchers()
        return result

    def popitem(self) -> tuple[K, V]:
        result = super().popitem()
        if self._ref.is_ready:
            self._ref._trigger_watchers()
        return result

    def update(self, *args: t.Any, **kwargs: V) -> None:
        for k, v in dict(*args, **kwargs).items():
            self[k] = v
        if self._ref.is_ready:
            self._ref._trigger_watchers()


class Ref(t.Generic[T]):
    __slots__ = (
        "_signals", "deep", "is_ready",
        "types", "links", "_value",
        "name", "asyncio_lock"
    )

    def __init__(
        self,
        value: T,
        *,
        name: str | None = None,
        delayed_init: bool = False,
        deep: bool = False,
        types: tuple[type, ...] | None = None
    ) -> None:
        self._signals = Signals({"changed"})
        self.deep = deep
        self.is_ready = not delayed_init
        self.types = types

        # It's links (refs) to objects that doesn't have to be removed by GC
        self.links: dict[int, t.Any] = {}

        self._value: T = self._wrap_if_mutable(value)

        self.name = name or "unknown"
        self.asyncio_lock = asyncio.Lock()
        if __debug__:
            logger.debug("Ref with name '%s' created", self.name)

    def _wrap_if_mutable(self, value: T) -> T:
        if not self.deep:
            if isinstance(value, list):
                return ReactiveList(value, self)  # type: ignore
            if isinstance(value, set):
                return ReactiveSet(value, self)  # type: ignore
            if isinstance(value, dict):
                return ReactiveDict(value, self)  # type: ignore
            return value

        def deep_wrap(val: T) -> T:
            if isinstance(val, list):
                return ReactiveList(  # type: ignore
                    [deep_wrap(item) for item in val],
                    self  # type: ignore
                )
            if isinstance(val, set):
                return ReactiveSet(  # type: ignore
                    {deep_wrap(item) for item in val},
                    self  # type: ignore
                )
            if isinstance(val, dict):
                return ReactiveDict(  # type: ignore
                    {k: deep_wrap(v) for k, v in val.items()},
                    self
                )
            return val

        return deep_wrap(value)

    async def __aenter__(self) -> t.Self:
        if __debug__:
            logger.debug("Ref '%s' started transaction", self.name)
        await self.asyncio_lock.acquire()
        if __debug__:
            logger.debug("Ref '%s' lock acquired", self.name)
        return self

    async def __aexit__(
        self,
        exc_type: t.Any,
        exc_val: t.Any,
        traceback: t.Any
    ) -> None:
        if __debug__:
            logger.debug("Ref '%s' lock released", self.name)
        self.asyncio_lock.release()
        if not exc_type:
            self._trigger_watchers()

    def _trigger_watchers(self, log: bool = True) -> None:
        if self.asyncio_lock.locked():
            return

        if not self.is_ready:
            return

        if "changed" in self._signals._blocked:
            return

        self._signals.notify("changed", self.value)

        if __debug__ and log:
            logger.debug(
                "Ref '%s' triggered watchers",
                self.name
            )

    @property
    def value(self) -> T:
        if not self.is_ready:
            logger.warning(
                "Trying to get value, ref '%s' is not ready!",
                self.name
            )
        return self._value

    @value.setter
    def value(self, _new_value: T) -> None:
        old_value = self._value
        new_value = self._wrap_if_mutable(_new_value)
        if old_value != new_value:
            if self.types:
                if not isinstance(new_value, self.types):
                    raise TypeError(
                        f"Types do not match {repr(new_value)}: " +
                        f"{type(new_value)} not in {self.types}"
                    )
            else:
                if not isinstance(old_value, type(new_value)):
                    raise TypeError(
                        f"Types do not match {repr(new_value)}: " +
                        f"{type(old_value)} != {type(new_value)}"
                    )
            if __debug__ and self.name:
                logger.debug("Ref '%s' changed value", self.name)

            self._value = new_value
            self._trigger_watchers(log=False)

    def unpack(self) -> T:
        def _unpack(value: t.Any) -> t.Any:
            if isinstance(value, ReactiveList):
                return [_unpack(item) for item in value]
            if isinstance(value, ReactiveSet):
                return {_unpack(item) for item in value}
            if isinstance(value, ReactiveDict):
                return {key: _unpack(val) for key, val in value.items()}
            return value

        return _unpack(self._value)

    def create_ref(self, object: t.Any) -> int:
        if self.links:
            new_id = list(self.links.keys())[-1] + 2
        else:
            new_id = 0
        self.links[new_id] = object

    def remove_ref(self, id: int) -> None:
        del self.links[id]

    def handlers_signal(self, signal_name: str) -> list[int]:
        return self._signals.handlers(signal_name)

    def handlers(self) -> list[int]:
        return self._signals.handlers("changed")

    def block_changed(self) -> None:
        self._signals.block("changed")

    def unblock_changed(self) -> None:
        self._signals.unblock("changed")

    def notify_signal(
        self,
        signal_name: str,
        *args: t.Any
    ) -> None:
        self._signals.notify(signal_name, *args)

    def watch_signal(
        self,
        signal_name: str,
        callback: t.Callable[[T], None],
        **kwargs: t.Any
    ) -> int:
        return self._signals.watch(signal_name, callback, **kwargs)

    def unwatch_signal(
        self, handler_id: int
    ) -> int:
        return self._signals.unwatch(handler_id)

    def watch(self, callback: t.Callable[[T], None], **kwargs: t.Any) -> int:
        if __debug__:
            logger.debug("Ref '%s' create watcher", self.name)
        return self._signals.watch("changed", callback, **kwargs)

    def unwatch(self, handler_id: int) -> None:
        if __debug__:
            logger.debug("Ref '%s' remove watcher", self.name)
        self._signals.unwatch_fast("changed", handler_id)

    def ready(self) -> None:
        self.is_ready = True

    def unbind(self, ref: "Ref[T]", handler_id: int) -> None:
        """Basically wrapper function. ref.unwatch() can be used as well"""
        ref.unwatch(handler_id)

    def bind(self, ref: "Ref[U]", transform: t.Callable[[U], T]) -> int:
        def on_changed(new_value: U) -> None:
            self.value = transform(new_value)

        handler_id = ref.watch(on_changed)
        return handler_id
