import signal
import typing as t
import types


class ExitSignals:
    SIGERROR = signal.SIGRTMIN + 1
    SIGHUNG = signal.SIGRTMIN + 2
    SIGRELOAD = signal.SIGRTMIN + 3


def exit_reload() -> None:
    signal.raise_signal(ExitSignals.SIGRELOAD)


def exit_hung() -> None:
    signal.raise_signal(ExitSignals.SIGHUNG)


def exit_error() -> None:
    signal.raise_signal(ExitSignals.SIGERROR)


def set_fatal_handler(
    callback: t.Callable[[int, types.FrameType | None], None]
) -> None:
    for sig in (
        signal.SIGTERM,
        signal.SIGINT,
        signal.SIGABRT,
        ExitSignals.SIGERROR,
        ExitSignals.SIGHUNG,
        ExitSignals.SIGRELOAD
    ):
        signal.signal(sig, callback)
