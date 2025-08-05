from repository import gtk, gdk, gio, gobject
import typing as t
from config import Settings
import src.widget as widget
from utils.styles import toggle_css_class
from utils.debounce import sync_debounce
import weakref


def test_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


int_kwargs: t.Any = {
    "transform_fn": lambda v: str(v),
    "transform2_fn": lambda v: int(v),
    "test_text": lambda v: str(v).isdecimal()
}

float_kwargs: t.Any = {
    "transform_fn": lambda v: str(v),
    "transform2_fn": lambda v: float(v),
    "test_text": test_float
}


class RowTemplate(gtk.Box):
    __gtype_name__ = "SettingsRowTemplate"

    def __init__(
        self,
        label: str,
        description: str | None,
        css_classes: tuple[str, ...] = (),
        clickable: bool = True,
        **props: t.Any
    ) -> None:
        super().__init__(
            css_classes=css_classes,
            **props
        )
        toggle_css_class(self, "clickable", clickable)
        if "valign" not in props:
            self.set_valign(gtk.Align.START)
        if "hexpand" not in props:
            self.set_hexpand(True)
        self.add_css_class("settings-row")

        self.info_box = gtk.Box(
            css_classes=("info-box",),
            orientation=gtk.Orientation.VERTICAL,
            hexpand=True,
            valign=gtk.Align.CENTER
        )
        self.label = gtk.Label(
            label=label,
            css_classes=("label",),
            xalign=0,
            valign=gtk.Align.CENTER
        )
        self.description: gtk.Label | None = None
        self.info_box.append(self.label)
        self.set_description(description)

        self.append(self.info_box)
        self.clickable = clickable
        if clickable:
            self.click_gesture = gtk.GestureClick.new()
            self.click_gesture.set_button(0)
            self.gesture_conn = (
                self.click_gesture.connect("released", self.on_click_released)
            )
            self.add_controller(self.click_gesture)

    def set_description(self, value: str | None) -> None:
        if value is not None:
            if self.description is None:
                self.description = gtk.Label(
                    label=value,
                    css_classes=("description",),
                    xalign=0,
                    valign=gtk.Align.CENTER
                )
                self.info_box.append(self.description)
            else:
                self.description.set_label(value)
        elif self.description is not None:
            self.info_box.remove(self.description)
            self.description = None

    def on_click(self) -> None:
        ...

    def on_secondary_click(self) -> None:
        ...

    def on_click_released(
        self,
        gesture: gtk.GestureClick,
        n_press: int,
        x: int,
        y: int
    ) -> None:
        button_number = gesture.get_current_button()
        if button_number == gdk.BUTTON_PRIMARY:
            self.on_click()
        elif button_number == gdk.BUTTON_SECONDARY:
            self.on_secondary_click()

    def destroy(self) -> None:
        if self.clickable:
            self.click_gesture.disconnect(self.gesture_conn)
            self.remove_controller(self.click_gesture)


class SwitchRowTemplate(RowTemplate):
    __gtype_name__ = "SettingsSwitchRowTemplate"

    def __init__(
        self,
        label: str,
        description: str | None,
        css_classes: tuple[str, ...] = (),
        **props: t.Any
    ) -> None:
        super().__init__(label, description, css_classes, **props)
        self.switch = widget.Switch(
            valign=gtk.Align.CENTER,
            tooltip_text="Toggle",
        )
        self.append(self.switch)
        self.switch_handler = self.switch.connect(
            "notify::active", self.on_switch_changed
        )

    def on_click(self) -> None:
        self.switch.activate()

    def on_switch_changed(self, *args: t.Any) -> None:
        ...

    def switch_set_active(self, value: bool) -> None:
        self.switch.handler_block(self.switch_handler)
        self.switch.set_active(value)
        self.switch.handler_unblock(self.switch_handler)

    def destroy(self) -> None:
        self.switch.disconnect(self.switch_handler)
        super().destroy()


class TextRowTemplate(RowTemplate):
    __gtype_name__ = "SettingsTextRowTemplate"

    def __init__(
        self,
        label: str,
        description: str | None,
        left_icon: str | None = None,
        right_icon: str | None = None,
        max_length: int | None = None,
        css_classes: tuple[str, ...] = (),
        max_width_chars: int | None = None,
        **props: t.Any
    ) -> None:
        super().__init__(label, description, css_classes, False, **props)

        self.entry_box = gtk.Box(
            css_classes=("entry-box",)
        )
        self.entry = gtk.Entry(
            css_classes=("entry",),
            halign=gtk.Align.END
        )
        if max_length:
            self.entry.set_max_length(max_length)

        if max_length or max_width_chars:
            self.entry.set_max_width_chars(max_length or max_width_chars or 0)

        self.entry_box.append(self.entry)
        if left_icon:
            self.left_icon = widget.Icon(
                left_icon,
                css_classes=("left",)
            )
            self.entry_box.prepend(self.left_icon)
        if right_icon:
            self.right_icon = widget.Icon(
                right_icon,
                css_classes=("right",)
            )
            self.entry_box.append(self.right_icon)
        self.append(self.entry_box)

        self.debounced_text_changed = sync_debounce(500)(self.on_text_changed)
        self.entry_handler = (
            self.entry.connect("notify::text", self.debounced_text_changed)
        )

    def entry_update_text(self, value: str) -> None:
        if self.entry.get_text() != value:
            self.entry.handler_block(self.entry_handler)
            self.entry.set_text(value)
            self.entry.handler_unblock(self.entry_handler)

    def destroy(self) -> None:
        super().destroy()
        self.entry.disconnect(self.entry_handler)

    def on_text_changed(self, *args: t.Any) -> None:
        ...


class DropdownItem(gobject.Object):
    def __init__(
        self,
        value: t.Any,
        label: str,
        tooltip: str | None = None
    ) -> None:
        super().__init__()
        self.label = label
        self.value = value
        self.tooltip = tooltip


class DropdownRowTemplate(RowTemplate):
    __gtype_name__ = "DropdownRowTemplate"

    def __init__(
        self,
        label: str,
        description: str | None,
        items: list[DropdownItem],
        css_classes: tuple[str, ...] = (),
        **props: t.Any
    ) -> None:
        super().__init__(label, description, css_classes, **props)

        self.items = gio.ListStore.new(DropdownItem)
        for item in items:
            self.items.append(item)

        self.factory = gtk.SignalListItemFactory()
        self.factory_handlers = (
            self.factory.connect("setup", self.on_setup),
            self.factory.connect("bind", self.on_bind)
        )

        self.dropdown = gtk.DropDown(
            model=self.items,
            factory=self.factory
        )

        self.dropdown_handler = self.dropdown.connect(
            "notify::selected",
            self.on_item_selected
        )

        self.append(self.dropdown)

    def set_items(self, items: list[DropdownItem]) -> None:
        self.items.remove_all()
        for item in items:
            self.items.append(item)

    def on_click(self) -> None:
        self.dropdown.activate()

    def on_setup(
        self,
        factory: gtk.SignalListItemFactory,
        list_item: gtk.ListItem
    ) -> None:
        label = gtk.Label(xalign=0)
        list_item.set_child(label)

    def on_bind(
        self,
        factory: gtk.SignalListItemFactory,
        list_item: gtk.ListItem
    ) -> None:
        item = t.cast(DropdownItem, list_item.get_item())
        label = t.cast(gtk.Label, list_item.get_child())
        label.set_text(item.label)
        if item.tooltip:
            label.set_tooltip_text(item.tooltip)

    def set_current(self, value: str) -> None:
        model = self.dropdown.get_model()
        if model is None:
            return
        for i in range(model.get_n_items()):
            item = t.cast(DropdownItem, model.get_item(i))
            if item.value == value:
                self.dropdown.set_selected(i)
                break

    def get_current(self) -> DropdownItem:
        return t.cast(DropdownItem, self.dropdown.get_selected_item())

    def destroy(self) -> None:
        super().destroy()
        for handler in self.factory_handlers:
            self.factory.disconnect(handler)
        self.dropdown.disconnect(self.dropdown_handler)

    def on_item_selected(self, *args: t.Any) -> None:
        ...


class Row(RowTemplate):
    __gtype_name__ = "SettingsRow2"

    def __init__(
        self,
        label: str,
        description: str,
        on_click: t.Callable[[t.Self], None] | None = None,
        on_secondary_click: t.Callable[[t.Self], None] | None = None,
        css_classes: tuple[str, ...] = (),
        clickable: bool | None = None,
        **props: t.Any
    ):
        if clickable is None:
            clickable = on_click is not None or on_secondary_click is not None
        self._on_click = (
            weakref.WeakMethod(on_click)
            if on_click else None
        )
        self._on_secondary_click = (
            weakref.WeakMethod(on_secondary_click)
            if on_secondary_click else None
        )
        super().__init__(label, description, css_classes, clickable, **props)

    def on_click(self) -> None:
        super().on_click()
        if self._on_click is None:
            return
        method = self._on_click()
        if callable(method):
            method(self)  # type: ignore

    def on_secondary_click(self) -> None:
        super().on_secondary_click()
        if self._on_secondary_click is None:
            return
        method = self._on_secondary_click()
        if callable(method):
            method(self)  # type: ignore


class SwitchRow(SwitchRowTemplate):
    __gtype_name__ = "SettingsSwitchRow2"

    def __init__(
        self,
        label: str,
        description: str | None,
        on_changed: t.Callable[[t.Self, bool], None],
        css_classes: tuple[str, ...] = (),
        **props: t.Any
    ) -> None:
        self._on_changed = weakref.WeakMethod(on_changed)
        super().__init__(label, description, css_classes, **props)

    def on_switch_changed(self, *args: t.Any) -> None:
        super().on_switch_changed(*args)
        method = self._on_changed()
        if callable(method):
            method(self, self.switch.get_active())  # type: ignore


class TextRow(TextRowTemplate):
    __gtype_name__ = "SettingsTextRow2"

    def __init__(
        self,
        label: str,
        description: str | None,
        on_text_changed: t.Callable[[t.Self, str], None],
        left_icon: str | None = None,
        right_icon: str | None = None,
        max_length: int | None = None,
        css_classes: tuple[str, ...] = (),
        max_width_chars: int | None = None,
        **props: t.Any
    ) -> None:
        self._on_text_changed = weakref.WeakMethod(on_text_changed)
        super().__init__(
            label, description, left_icon, right_icon,
            max_length, css_classes, max_width_chars,
            **props
        )

    def on_text_changed(self, *args: t.Any) -> None:
        method = self._on_text_changed()
        if callable(method):
            method(self, self.entry.get_text())  # type: ignore


class DropdownRow(DropdownRowTemplate):
    __gtype_name__ = "SettingsDropdownRow2"

    def __init__(
        self,
        label: str,
        description: str | None,
        items: list[DropdownItem],
        on_selected: t.Callable[[t.Self, DropdownItem], None],
        css_classes: tuple[str, ...] = (),
        **props: t.Any
    ) -> None:
        self._on_selected = weakref.WeakMethod(on_selected)
        super().__init__(label, description, items, css_classes, **props)

    def on_item_selected(self, *args: t.Any) -> None:
        super().on_item_selected(*args)
        method = self._on_selected()
        if callable(method):
            method(self, self.get_current())  # type: ignore


class SettingsBoolRow(SwitchRowTemplate):
    __gtype_name__ = "SettingsBoolRow"

    def __init__(
        self,
        label: str,
        description: str | None,
        key: str,
        css_classes: tuple[str, ...] = (),
        **props: t.Any
    ) -> None:
        super().__init__(label, description, css_classes, **props)
        self.key = key
        self.settings = Settings()
        self.settings_handler = self.settings.watch(
            key, self.switch_set_active, True
        )

    def on_switch_changed(self, *args: t.Any) -> None:
        self.settings.set(self.key, self.switch.get_active())

    def destroy(self) -> None:
        self.settings.unwatch(self.settings_handler)


class SettingsTextRow(TextRowTemplate):
    __gtype_name__ = "SettingsTextRow"

    def __init__(
        self,
        label: str,
        description: str | None,
        key: str,
        left_icon: str | None = None,
        right_icon: str | None = None,
        max_length: int | None = None,
        transform_fn: t.Callable[[t.Any], str] | None = None,
        transform2_fn: t.Callable[[str], t.Any] | None = None,
        test_text: t.Callable[[str], bool] | None = None,
        css_classes: tuple[str, ...] = (),
        max_width_chars: int | None = None,
        **props: t.Any
    ) -> None:
        self.key = key
        self.transform_fn = transform_fn
        self.transform2_fn = transform2_fn
        self.test_text = test_text
        self.settings = Settings()
        super().__init__(
            label, description, left_icon, right_icon,
            max_length, css_classes, max_width_chars,
            **props
        )

        self.settings_handler = self.settings.watch(
            key, self.on_setting_updated
        )

    def on_setting_updated(self, new_value: t.Any) -> None:
        value = (
            self.transform_fn(new_value)
            if self.transform_fn
            else str(new_value)
        )
        self.entry_update_text(value)

    def destroy(self) -> None:
        super().destroy()
        self.settings.unwatch(self.settings_handler)

    def on_text_changed(self, *args: t.Any) -> None:
        text = self.entry.get_text()
        if self.test_text and not self.test_text(text):
            toggle_css_class(self.entry_box, "incorrect", True)
            return
        toggle_css_class(self.entry_box, "incorrect", False)

        value = (
            self.transform2_fn(text)
            if self.transform2_fn
            else text
        )
        self.settings.set(self.key, value)


class SettingsDropdownRow(DropdownRowTemplate):
    __gtype_name__ = "SettingsDropdownRow"

    def __init__(
        self,
        label: str,
        description: str | None,
        key: str,
        items: list[DropdownItem],
        css_classes: tuple[str, ...] = (),
        **props: t.Any
    ) -> None:
        self.key = key
        self.settings = Settings()
        super().__init__(label, description, items, css_classes, **props)

        self.settings_handler = self.settings.watch(
            key, self.set_current
        )

    def destroy(self) -> None:
        super().destroy()
        self.settings.unwatch(self.settings_handler)

    def on_item_selected(self, *args: t.Any) -> None:
        item = self.get_current()
        self.settings.set(self.key, item.value)


class Category(gtk.Label):
    __gtype_name__ = "SettingsCategoryLabel"

    def __init__(self, text: str) -> None:
        super().__init__(
            css_classes=("settings-category",),
            label=text,
            hexpand=True,
            xalign=0
        )

    def destroy(self) -> None:
        ...


class Hint(gtk.Label):
    __gtype_name__ = "SettingsHintLabel"

    def __init__(self, text: str) -> None:
        super().__init__(
            css_classes=("settings-hint",),
            label=text,
            hexpand=True,
            halign=gtk.Align.CENTER,
            justify=gtk.Justification.CENTER
        )

    def destroy(self) -> None:
        ...
