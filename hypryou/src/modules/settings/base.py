from repository import gtk, gdk
import typing as t
from config import Settings
import src.widget as widget


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


class Category(gtk.Label):
    __gtype_name__ = "SettingsCategoryLabel"

    def __init__(self, text: str) -> None:
        super().__init__(
            css_classes=("settings-category",),
            label=text,
            hexpand=True,
            xalign=0
        )
