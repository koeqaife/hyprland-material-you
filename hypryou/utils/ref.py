import asyncio
import typing as t
from collections.abc import MutableSequence, MutableSet
from utils.logger import logger
from utils.service import Signals

# I wanted to make weakref for watchers
# but it's to difficult for me heh

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
        value: L | t.Iterable[L],
    ) -> None:
        if isinstance(index, int) and not isinstance(value, t.Iterable):
            self._data[index] = value
        elif isinstance(index, slice) and isinstance(value, t.Iterable):
            self._data[index] = value

        if self._ref.is_ready:
            self._ref._trigger_watchers()

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

    def insert(self, i: int, value: L) -> None:
        self._data.insert(i, value)

        if self._ref.is_ready:
            self._ref._trigger_watchers()

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return repr(self._data)


class ReactiveSet(MutableSet[L], t.Generic[L]):
    def __init__(self, data: set[L], ref: "Ref[set[L]]"):
        self._data = data
        self._ref = ref

    def __contains__(self, item: object) -> bool:
        return item in self._data

    def __iter__(self) -> t.Iterator[L]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def add(self, value: L) -> None:
        if value not in self._data:
            self._data.add(value)

            if self._ref.is_ready:
                self._ref._trigger_watchers()

    def discard(self, value: L) -> None:
        if value in self._data:
            self._data.discard(value)

            if self._ref.is_ready:
                self._ref._trigger_watchers()

    def __repr__(self) -> str:
        return repr(self._data)


class ReactiveDict(dict[K, V], t.Generic[K, V]):
    def __init__(self, data: dict[K, V], parent_ref: 'Ref[t.Any]') -> None:
        super().__init__()
        self._ref = parent_ref
        for k, v in data.items():
            self[k] = v

    def __setitem__(self, key: K, value: V) -> None:
        wrapped_value = self._ref._wrap_if_mutable(value)
        super().__setitem__(key, wrapped_value)

        if self._ref.is_ready:
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
    def __init__(
        self,
        value: T,
        name: str | None = None,
        delayed_init: bool = False,
        deep: bool = False,
        types: tuple[type, ...] | None = None
    ) -> None:
        self._signals = Signals()
        self.deep = deep
        self.is_ready = not delayed_init
        self.types = types

        self._value = self._wrap_if_mutable(value)

        self.name = name or "unknown"
        self.asyncio_lock = asyncio.Lock()
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
        logger.debug("Ref '%s' started transaction", self.name)
        await self.asyncio_lock.acquire()
        logger.debug("Ref '%s' lock acquired", self.name)
        return self

    async def __aexit__(
        self,
        exc_type: t.Any,
        exc_val: t.Any,
        traceback: t.Any
    ) -> None:
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

        if log:
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
    def value(self, new_value: T) -> None:
        old_value = self._value
        new_value = self._wrap_if_mutable(new_value)
        if old_value != new_value:
            assert self.types or isinstance(old_value, type(new_value)), (
                f"Types do not match: {type(old_value)} != {type(new_value)}"
            )
            assert not self.types or isinstance(new_value, self.types), (
                f"Types do not match: {type(new_value)} not in {self.types}"
            )
            if self.name:
                logger.debug("Ref '%s' changed value", self.name)

            self._value = new_value
            self._trigger_watchers(log=False)

    def watch(self, callback: t.Callable[[T], None], **kwargs: t.Any) -> int:
        logger.debug("Ref '%s' create watcher", self.name)
        return self._signals.watch("changed", callback, **kwargs)

    def unwatch(self, handler_id: int) -> None:
        logger.debug("Ref '%s' remove watcher", self.name)
        self._signals.unwatch("changed", handler_id)

    def ready(self) -> None:
        self.is_ready = True

    def unbind(self, ref: "Ref[T]", handler_id: int) -> None:
        """Basically helper function. ref.unwatch() can be used as well"""
        ref.unwatch(handler_id)

    def bind(self, ref: "Ref[U]", transform: t.Callable[[U], T]) -> int:
        def on_changed(new_value: T) -> None:
            self.value = transform(new_value)  # type: ignore [arg-type]

        handler_id = ref.watch(on_changed)  # type: ignore [arg-type]
        return handler_id
