from dataclasses import dataclass
from enum import Enum

main_mod = "SUPER"


class Category(str, Enum):
    ACTIONS = "Actions"
    TOOLS = "Tools"
    APPS = "Applications"
    WINDOWS = "Windows"
    WORKSPACES = "Workspaces"
    MISC = "Misc"


@dataclass
class KeyBind:
    bind: tuple[str, ...]
    action: tuple[str, ...] | str
    description: str | None = None
    category: Category | None = None

    @property
    def id(self) -> str:
        return "_".join(self.bind)


@dataclass
class KeyBindOverride:
    id: str
    bind: tuple[str, ...] | None
    action: tuple[str, ...] | str | None


@dataclass
class KeyBindHint:
    bind: tuple[str, ...]
    description: str | None = None
    category: Category | None = None
