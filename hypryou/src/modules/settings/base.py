from repository import gtk, gdk
import typing as t


class RowTemplate(gtk.Box):
    __gtype_name__ = "SettingsRowTemplate"

    def __init__(
        self,
        label: str,
        description: str | None,
        css_classes: tuple[str, ...],
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
