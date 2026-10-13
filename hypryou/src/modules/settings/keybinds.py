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
from utils.ref import Ref, unpack_reactive
import src.widget as widget
from config import Settings

from src.modules.settings.base import RowTemplate
from src.modules.settings.base import Category
from src.modules.settings.base import Hint
from src.modules.settings.base import EditableList, EditableListRow

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


def parse_bind(text: str) -> list[str]:
    return [
        normalize_key(part)
        for part in re.split(split_regex, text)
        if part.strip()
    ]


def bind_problem(parts: list[str]) -> str | None:
    if len(parts) > 3:
        return "Too many modifiers (max 3)."
    if len(parts) < 1:
        return "Too few modifiers (min 1)."
    return None


def get_disabled() -> list[str]:
    disabled = unpack_reactive(Settings().get("disabled_keybinds"))
    return list(disabled) if isinstance(disabled, list) else []


def taken_keys() -> dict[str, str]:
    """Every key the default binds still hold, with what they do."""
    keys: dict[str, str] = {}
    disabled = get_disabled()
    for keybind in key_binds:
        if not isinstance(keybind, KeyBind) or keybind.id in disabled:
            continue
        bind = keybind.bind
        override = keybind_overrides.value.get(keybind.id)
        if override is not None and override.bind:
            bind = override.bind
        name = keybind.description or keybind.id
        joined = " + ".join(bind).upper()
        if "%N%" in joined:
            for n in range(10):
                keys[joined.replace("%N%", str(n))] = name
        else:
            keys[joined] = name
    return keys


class KeybindRow(RowTemplate):
    __gtype_name__ = "SettingsKeybindRow"

    def __init__(
        self,
        keybind: KeyBind,
        on_bind_text: t.Callable[[t.Self, list[str] | None], None],
        on_action_text: t.Callable[[t.Self, list[str] | None], None],
        on_disable: t.Callable[[t.Self, bool], None]
    ) -> None:
        self.keybind = keybind
        self._on_disable = weakref.WeakMethod(on_disable)
        self.disabled = False
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

        self.disable = gtk.Button(
            css_classes=("icon-tonal", "disable-button"),
            child=widget.Icon("block"),
            tooltip_text="Disable",
            valign=gtk.Align.CENTER,
            halign=gtk.Align.CENTER
        )

        self.handlers = {
            self.disable: self.disable.connect(
                "clicked", self.on_disable_clicked
            ),
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
        self.hbox.append(self.disable)
        self.append(self.hbox)
        self.update()

    def set_disabled(self, disabled: bool) -> None:
        self.disabled = disabled
        self.entries_box.set_sensitive(not disabled)
        self.reset.set_visible(not disabled)
        self.disable.set_tooltip_text("Enable" if disabled else "Disable")
        icon = self.disable.get_child()
        if isinstance(icon, gtk.Label):
            icon.set_label("check_circle" if disabled else "block")

    def on_disable_clicked(self, *args: t.Any) -> None:
        self.set_disabled(not self.disabled)
        callback = self._on_disable()
        if callable(callback):
            callback(self, self.disabled)  # type: ignore

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
        self.set_disabled(self.keybind.id in get_disabled())
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

        binds = parse_bind(self.bind_entry.get_text())
        problem = bind_problem(binds)

        if problem:
            toggle_css_class(self.bind_entry, "incorrect", True)
            self.bind_entry.set_tooltip_text(problem)
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


class CustomKeybindRow(EditableListRow):
    __gtype_name__ = "SettingsCustomKeybindRow"

    def __init__(
        self,
        value: dict[str, str],
        on_remove: t.Callable[[t.Self], None],
        on_changed: t.Callable[[], None]
    ) -> None:
        # Laid out like the default binds: the name as the title, the key
        # and the command under it, the button on the right.
        super().__init__(on_remove, ("keybind-row", "custom-keybind-row"))
        self._on_changed = weakref.WeakMethod(on_changed)
        self.set_orientation(gtk.Orientation.VERTICAL)
        self.remove(self.fields)
        self.remove(self.remove_button)

        self.name_entry = gtk.Entry(
            css_classes=("name-entry",),
            placeholder_text="Name",
            halign=gtk.Align.START
        )
        self.entries_box = gtk.Box(
            css_classes=("entries-box",),
            homogeneous=True,
            hexpand=True
        )
        self.bind_entry = gtk.Entry(
            css_classes=("bind-entry",),
            placeholder_text="Super + T"
        )
        self.command_entry = gtk.Entry(
            css_classes=("action-entry",),
            placeholder_text="Command or hl.dsp action"
        )
        self.name_entry.set_text(value.get("name") or "")
        self.bind_entry.set_text(value.get("bind") or "")
        self.command_entry.set_text(value.get("command") or "")
        self.entries_box.append(self.bind_entry)
        self.entries_box.append(self.command_entry)
        self.hbox = gtk.Box(hexpand=True)
        self.hbox.append(self.entries_box)
        self.hbox.append(self.remove_button)
        self.append(self.name_entry)
        self.append(self.hbox)

        self.debounced_changed = sync_debounce(500)(self.on_changed)
        self.handlers = {
            entry: entry.connect("notify::text", self.debounced_changed)
            for entry in (
                self.name_entry, self.bind_entry, self.command_entry
            )
        }

    def on_changed(self, *args: t.Any) -> None:
        method = self._on_changed()
        if callable(method):
            method()  # type: ignore

    def set_problem(self, entry: gtk.Entry, problem: str | None) -> None:
        toggle_css_class(entry, "incorrect", bool(problem))
        entry.set_tooltip_text(problem)

    def get_value(self) -> dict[str, str]:
        return {
            "name": self.name_entry.get_text().strip(),
            "bind": " + ".join(parse_bind(self.bind_entry.get_text())),
            "command": self.command_entry.get_text().strip()
        }

    def destroy(self) -> None:
        for entry, handler in self.handlers.items():
            entry.disconnect(handler)
        super().destroy()


class CustomKeybindsList(EditableList):
    __gtype_name__ = "SettingsCustomKeybindsList"

    def __init__(self, on_dirty: t.Callable[[], None]) -> None:
        self._on_dirty = weakref.WeakMethod(on_dirty)
        super().__init__(
            "Custom keybinds",
            "Your own binds on top of the defaults",
            "custom_keybinds",
            "Add bind"
        )

    def create_row(self, value: dict[str, str]) -> EditableListRow:
        return CustomKeybindRow(value, self.on_remove, self.save)

    def empty_value(self) -> dict[str, str]:
        return {"name": "", "bind": "", "command": ""}

    def save(self, *args: t.Any) -> None:
        # The rest of the page waits for Save, so this list does too.
        if self._loading:
            return
        self.validate()
        callback = self._on_dirty()
        if callable(callback):
            callback()

    def commit(self) -> None:
        super().save()

    def validate(self) -> None:
        taken = taken_keys()
        seen: set[str] = set()
        for row in self.rows:
            if not isinstance(row, CustomKeybindRow):
                continue
            value = row.get_value()
            parts = parse_bind(row.bind_entry.get_text())
            empty = not row.bind_entry.get_text().strip()
            problem = None if empty else bind_problem(parts)
            key = value["bind"]
            if problem is None and key in taken:
                problem = (
                    f"Also runs \"{taken[key]}\". "
                    "Disable that bind below to free the key"
                )
            elif problem is None and key and key in seen:
                problem = "Another custom bind above uses this key"
            if key:
                seen.add(key)
            row.set_problem(row.bind_entry, problem)
            row.set_problem(
                row.command_entry,
                "Nothing to run" if key and not value["command"] else None
            )


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
        self.disabled_changes: dict[str, bool] = {}
        self.custom_dirty = False

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
            row = KeybindRow(
                keybind,
                self.on_bind_text,
                self.on_action_text,
                self.on_disable
            )
            self.box_children.append(row)

        self.box_children.append(Category("Custom"))
        self.custom_list = CustomKeybindsList(self.on_custom_changed)
        self.box_children.append(self.custom_list)
        self.box_children.append(Hint(
            "Runs a command, or an hl.dsp action like the binds above. "
            "Disable a default bind to free its key"
        ))

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

    def on_custom_changed(self) -> None:
        self.custom_dirty = True
        self.save_button.set_sensitive(True)

    def on_cancel(self, *args: t.Any) -> None:
        self.overrides.clear()
        self.disabled_changes.clear()
        if self.custom_dirty:
            self.custom_dirty = False
            self.custom_list.load()
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

        if self.disabled_changes:
            disabled = get_disabled()
            for id, is_disabled in self.disabled_changes.items():
                if is_disabled and id not in disabled:
                    disabled.append(id)
                elif not is_disabled and id in disabled:
                    disabled.remove(id)
            Settings().set("disabled_keybinds", disabled)
            self.disabled_changes.clear()
        if self.custom_dirty:
            self.custom_dirty = False
            self.custom_list.commit()
        # A key that was taken may be free now, or the other way round.
        self.custom_list.validate()

        self.save_button.set_sensitive(False)

    def on_disable(self, row: KeybindRow, disabled: bool) -> None:
        self.disabled_changes[row.keybind.id] = disabled
        self.save_button.set_sensitive(True)

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
