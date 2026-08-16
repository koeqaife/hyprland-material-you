from dataclasses import dataclass
from enum import Enum

main_mod = "SUPER"


def serialize_string(string: str) -> str:
    return string.replace("\"", '\\"')


def make_exec(exec: str) -> str:
    return f"hl.dsp.exec_cmd(\"{serialize_string(exec)}\")"


def make_dispatch(string: str) -> str:
    return f"hl.dsp.{string}"


def make_hyprctl_dispatch(string: str) -> str:
    return f"hyprctl dispatch 'hl.dsp.{string}'"


class Category(str, Enum):
    ACTIONS = "Actions"
    TOOLS = "Tools"
    WINDOWS = "Window management"
    APPS = "Applications"


@dataclass
class KeyBind:
    bind: tuple[str, ...]
    action: str
    description: str | None = None
    category: Category | None = None

    @property
    def id(self) -> str:
        return "_".join(self.bind)


@dataclass
class KeyBindOverride:
    id: str
    bind: tuple[str, ...] | None
    action: str | None


@dataclass
class KeyBindHint:
    bind: tuple[str, ...]
    description: str | None = None
    category: Category | None = None
