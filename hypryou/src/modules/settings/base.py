from repository import gtk, gdk
import typing as t
from config import Settings
import src.widget as widget
from utils import sync_debounce


class RowTemplate(gtk.Box):
    __gtype_name__ = "SettingsRowTemplate"

    def __init__(
        self,
        label: str,
        description: str | None,
        css_classes: tuple[str, ...] = (),
        **props: t.Any
    ) -> None:
        super().__init__(
            css_classes=css_classes,
            **props
        )
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


class SettingsTextRow(RowTemplate):
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
        **props: t.Any
    ) -> None:
        self.key = key
        self.transform_fn = transform_fn
        self.transform2_fn = transform2_fn
        self.test_text = test_text
        self.settings = Settings()
        super().__init__(label, description, css_classes, **props)

        self.entry_box = gtk.Box(
            css_classes=("entry-box",)
        )
        self.entry = gtk.Entry(
            css_classes=("entry",),
            halign=gtk.Align.END
        )
        if max_length:
            self.entry.set_max_length(max_length)
            self.entry.set_max_width_chars(max_length)

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

        self.debounced_text_changed = sync_debounce(500)(self.text_changed)
        self.entry_handler = (
            self.entry.connect("notify::text", self.debounced_text_changed)
        )
        self.settings_handler = self.settings.watch(
            key, self.setting_updated
        )

    def setting_updated(self, new_value: t.Any) -> None:
        value = (
            self.transform_fn(new_value)
            if self.transform_fn
            else str(new_value)
        )
        if self.entry.get_text() != value:
            self.entry.handler_block(self.entry_handler)
            self.entry.set_text(value)
            self.entry.handler_unblock(self.entry_handler)

    def destroy(self) -> None:
        super().destroy()
        self.entry.disconnect(self.entry_handler)

    def text_changed(self, *args: t.Any) -> None:
        text = self.entry.get_text()
        if self.test_text and not self.test_text(text):
            new_value = self.settings.get(self.key)
            value = (
                self.transform_fn(new_value)
                if self.transform_fn
                else new_value
            )
            self.entry.handler_block(self.entry_handler)
            self.entry.set_text(value)
            self.entry.handler_unblock(self.entry_handler)
            return

        value = (
            self.transform2_fn(text)
            if self.transform2_fn
            else text
        )
        self.settings.set(self.key, value)


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
