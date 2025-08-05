from repository import gtk
from src.services.hyprland_keybinds.common import KeyBind
from src.services.hyprland_keybinds import key_binds
from src.services.hyprland_config import keybind_overrides
from src.services.hyprland_config import KeybindOverridesRaw
import re
import typing as t
import weakref
from utils.styles import toggle_css_class
from utils.debounce import sync_debounce
from utils.ref import Ref
import src.widget as widget
from config import Settings

from src.modules.settings.base import RowTemplate
from src.modules.settings.base import Category

split_regex = re.compile(r"[,+\s]+")
REPLACEMENTS: dict[str, str] = {
    "/": "SLASH",
    "-": "MINUS",
    "+": "PLUS",
    ".": "PERIOD",
    ",": "COMMA",
    ";": "SEMICOLON",
    "`": "GRAVE",
    "=": "EQUAL",
    "[": "BRACKETLEFT",
    "]": "BRACKETRIGHT",
    "\\": "BACKSLASH",
    "'": "APOSTROPHE"
}


def normalize_key(part: str) -> str:
    part = part.strip().upper()
    return REPLACEMENTS.get(part, part)


class KeybindRow(RowTemplate):
    __gtype_name__ = "SettingsKeybindRow"

    def __init__(
        self,
        keybind: KeyBind,
        on_bind_text: t.Callable[[t.Self, list[str] | None], None],
        on_action_text: t.Callable[[t.Self, list[str] | None], None]
    ) -> None:
        self.keybind = keybind
        self._on_bind_text = weakref.WeakMethod(on_bind_text)
        self._on_action_text = weakref.WeakMethod(on_action_text)

        super().__init__(
            self.keybind.description or "Uknown",
            description=None,
            css_classes=("keybind-row",),
            clickable=False
        )
        self.hbox = gtk.Box(
            hexpand=True
        )
        self.entries_box = gtk.Box(
            css_classes=("entries-box",),
            homogeneous=True,
            hexpand=True
        )
        self.bind_entry = gtk.Entry(
            css_classes=("bind-entry",),
            placeholder_text="Keybind"
        )
        self.action_entry = gtk.Entry(
            css_classes=("action-entry",),
            placeholder_text="Action"
        )

        self.debounced_on_bind_text = sync_debounce(500)(self.on_bind_text)
        self.debounced_on_action_text = sync_debounce(500)(self.on_action_text)

        self.reset = gtk.Button(
            css_classes=("icon-tonal", "reset-button"),
            child=widget.Icon("reset_settings"),
            tooltip_text="Reset",
            valign=gtk.Align.CENTER,
            halign=gtk.Align.CENTER,
            sensitive=False
        )

        self.handlers = {
            self.bind_entry: self.bind_entry.connect(
                "notify::text", self.debounced_on_bind_text
            ),
            self.action_entry: self.action_entry.connect(
                "notify::text", self.debounced_on_action_text
            ),
            self.reset: self.reset.connect(
                "clicked", self.on_reset
            )
        }

        self.set_orientation(gtk.Orientation.VERTICAL)
        self.entries_box.append(self.bind_entry)
        self.entries_box.append(self.action_entry)
        self.hbox.append(self.entries_box)
        self.hbox.append(self.reset)
        self.append(self.hbox)
        self.update()

    def on_reset(self, *args: t.Any) -> None:
        bind = self.keybind.bind
        action = self.keybind.action

        self.bind_entry.handler_block(self.handlers[self.bind_entry])
        self.action_entry.handler_block(self.handlers[self.action_entry])
        self.bind_entry.set_text(
            " + ".join([_bind.capitalize() for _bind in bind])
        )
        self.action_entry.set_text(
            ", ".join(action)
            if isinstance(action, tuple)
            else action
        )
        self.bind_entry.handler_unblock(self.handlers[self.bind_entry])
        self.action_entry.handler_unblock(self.handlers[self.action_entry])

        _on_bind_text = self._on_bind_text()
        _on_action_text = self._on_action_text()
        if callable(_on_bind_text):
            _on_bind_text(self, None)  # type: ignore
        if callable(_on_action_text):
            _on_action_text(self, None)  # type: ignore
        self.reset.set_sensitive(False)

    def update(self) -> None:
        self.reset.set_sensitive(False)
        override = keybind_overrides.value.get(self.keybind.id)
        bind = self.keybind.bind
        action = self.keybind.action
        if override is not None:
            if override.bind:
                bind = override.bind
                self.reset.set_sensitive(True)
            if override.action:
                action = override.action
                self.reset.set_sensitive(True)

        self.bind_entry.handler_block(self.handlers[self.bind_entry])
        self.action_entry.handler_block(self.handlers[self.action_entry])
        self.bind_entry.set_text(
            " + ".join([_bind.capitalize() for _bind in bind])
        )
        self.action_entry.set_text(
            ", ".join(action)
            if isinstance(action, tuple)
            else action
        )
        self.bind_entry.handler_unblock(self.handlers[self.bind_entry])
        self.action_entry.handler_unblock(self.handlers[self.action_entry])

    def on_bind_text(self, *args: t.Any) -> None:
        callback = self._on_bind_text()
        if not callable(callback):
            return

        text = self.bind_entry.get_text()
        binds = [
            normalize_key(part)
            for part in re.split(split_regex, text)
            if part.strip()
        ]

        if len(binds) > 3:
            toggle_css_class(self.bind_entry, "incorrect", True)
            self.bind_entry.set_tooltip_text("Too many modifiers (max 3).")
        elif len(binds) < 1:
            toggle_css_class(self.bind_entry, "incorrect", True)
            self.bind_entry.set_tooltip_text("Too few modifiers (min 1).")
        else:
            toggle_css_class(self.bind_entry, "incorrect", False)
            self.bind_entry.set_tooltip_text(None)
            callback(self, binds)  # type: ignore
            self.reset.set_sensitive(True)

    def on_action_text(self, *args: t.Any) -> None:
        callback = self._on_action_text()
        if not callable(callback):
            return

        text = self.action_entry.get_text()
        binds = [
            part.strip()
            for part in text.split(",")
            if part.strip()
        ]

        if len(binds) < 1:
            toggle_css_class(self.action_entry, "incorrect", True)
            self.action_entry.set_tooltip_text("Too few modifiers (min 1).")
        else:
            toggle_css_class(self.action_entry, "incorrect", False)
            self.action_entry.set_tooltip_text(None)
            callback(self, binds)  # type: ignore
            self.reset.set_sensitive(True)

    def destroy(self) -> None:
        super().destroy()
        for button, handler in self.handlers.items():
            button.disconnect(handler)


class KeybindsPage(gtk.Box):
    __gtype_name__ = "SettingsKeybindsPage"

    def __init__(self) -> None:
        self.box = gtk.Box(
            css_classes=("page-box",),
            orientation=gtk.Orientation.VERTICAL
        )
        self.scrollable = gtk.ScrolledWindow(
            hscrollbar_policy=gtk.PolicyType.NEVER,
            child=self.box,
            vexpand=True
        )
        super().__init__(
            css_classes=("keybinds-page", "settings-page",),
            orientation=gtk.Orientation.VERTICAL,
            vexpand=True
        )
        self.box_children: list[RowTemplate | Category] = []
        self.overrides: dict[str, dict[str, list[str] | None]] = {}

        added_categories: list[str] = []
        for keybind in key_binds:
            if not isinstance(keybind, KeyBind):
                continue
            if not keybind.description:
                continue
            category = keybind.category or "Uknown"
            if category not in added_categories:
                self.box_children.append(Category(category))
                added_categories.append(category)
            row = KeybindRow(keybind, self.on_bind_text, self.on_action_text)
            self.box_children.append(row)

        for child in self.box_children:
            self.box.append(child)

        self.actions_box = gtk.Box(
            css_classes=("actions-box",),
            halign=gtk.Align.END
        )
        self.save_button = gtk.Button(
            css_classes=("filled",),
            label="Save",
            sensitive=False
        )
        self.cancel_button = gtk.Button(
            css_classes=("text",),
            label="Cancel"
        )

        self.button_handlers = {
            self.cancel_button: self.cancel_button.connect(
                "clicked", self.on_cancel
            ),
            self.save_button: self.save_button.connect(
                "clicked", self.on_save
            )
        }

        self.actions_box.append(self.cancel_button)
        self.actions_box.append(self.save_button)
        self.append(self.scrollable)
        self.append(self.actions_box)

    def on_cancel(self, *args: t.Any) -> None:
        self.overrides.clear()
        for child in self.box_children:
            if isinstance(child, KeybindRow):
                child.update()
        self.save_button.set_sensitive(False)

    def on_save(self, *args: t.Any) -> None:
        overrides: Ref[KeybindOverridesRaw] = Settings().get_ref(
            "keybinds_overrides"
        )
        _map = {
            str(item["id"]): item
            for item in overrides.value
        }
        for id, to_change in self.overrides.items():
            if id not in _map:
                _map[id] = overrides._wrap_if_mutable({    # type: ignore
                    "id": id
                })
                overrides.value.append(_map[id])

            if "bind" in to_change:
                if to_change["bind"] is None:
                    if "bind" in _map[id]:
                        del _map[id]["bind"]
                else:
                    _map[id]["bind"] = to_change["bind"]

            if "action" in to_change:
                if to_change["action"] is None:
                    if "action" in _map[id]:
                        del _map[id]["action"]
                else:
                    _map[id]["action"] = to_change["action"]

        self.overrides.clear()
        self.save_button.set_sensitive(False)

    def on_bind_text(
        self,
        row: KeybindRow,
        bind: list[str] | None
    ) -> None:
        id = row.keybind.id
        if id not in self.overrides.keys():
            self.overrides[id] = {}

        self.overrides[id]["bind"] = bind
        self.save_button.set_sensitive(True)

    def on_action_text(
        self,
        row: KeybindRow,
        action: list[str] | None
    ) -> None:
        id = row.keybind.id
        if id not in self.overrides.keys():
            self.overrides[id] = {}

        self.overrides[id]["action"] = action
        self.save_button.set_sensitive(True)

    def destroy(self) -> None:
        for child in self.box_children:
            child.destroy()
