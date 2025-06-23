from utils import capitalize_first
from utils.logger import logger
from repository import gtk, layer_shell, gdk, glib
from src.services.system_tray import StatusNotifierItem, items
from config import HyprlandVars
import weakref
import typing as t
from src import widget

# It's so cool that when tray isn't opened there isn't any load to CPU
# Cause it's not listening to any updates of items


class TrayItem(gtk.Box):
    def __init__(self, item: StatusNotifierItem) -> None:
        super().__init__(
            valign=gtk.Align.START,
            hexpand=True,
            css_classes=("tray-item",)
        )
        self._item = item

        btn_box = gtk.Box(
            hexpand=True,
            halign=gtk.Align.END
        )
        self.quit_btn = gtk.Button(
            label="Quit",
            halign=gtk.Align.END,
            css_classes=("attention-outlined",)
        )
        btn_box.append(self.quit_btn)

        self.children = (
            gtk.Image(),
            gtk.Label(
                css_classes=("app-label",)
            ),
            btn_box
        )
        self.update_label()
        self.idle_update_image()
        for child in self.children:
            self.append(child)

        self.click_gesture = gtk.GestureClick.new()
        self.click_gesture.set_button(0)
        self.gesture_conn = (
            self.click_gesture.connect("released", self.on_click_released)
        )
        self.add_controller(self.click_gesture)
        self.quit_conn = self.quit_btn.connect("clicked", self.quit)
        self.update_visible()

        self.handler_id = self._item.watch("changed", self.on_changed)
        # weakref.finalize(self, lambda: logger.debug("TrayWidget finalized"))

    def on_changed(self, data: dict[str, t.Any] | None = None) -> None:
        if data:
            to_change = {
                "icon": self.idle_update_image,
                "title": self.update_label,
                "tooltip": self.update_label
            }.get(data["prop"])
            if to_change:
                to_change()
        else:
            self.idle_update_image()
            self.update_label()

    def quit(self, widget: gtk.Widget) -> None:
        self._item.quit()

    def on_click_released(
        self,
        gesture: gtk.GestureClick,
        n_press: int,
        x: int,
        y: int
    ) -> None:
        button_number = gesture.get_current_button()
        if button_number == gdk.BUTTON_PRIMARY:
            self._item.activate(x, y)
        elif button_number == gdk.BUTTON_SECONDARY:
            self._item.secondary_activate(x, y)

    def update_visible(self) -> None:
        self.set_visible(
            self._item.status is not None
        )

    def idle_update_image(self) -> None:
        glib.idle_add(self.update_image)

    def update_image(self) -> None:
        if not self.get_visible():
            return
        item = self._item
        image = self.children[0]
        theme = item.icon_theme
        if theme and theme.has_icon(item.icon_name):
            texture = theme.lookup_icon(
                item.icon_name,
                None,
                32,
                1,
                gtk.TextDirection.RTL,
                gtk.IconLookupFlags.FORCE_SYMBOLIC
            )
            image.set_from_paintable(texture)
        elif (pixbuf := item.get_pixbuf(32, 32)) is not None:
            image.set_from_pixbuf(pixbuf)
        else:
            image.set_from_icon_name(item.icon_name)
        image.set_size_request(32, 32)

    def update_label(self) -> None:
        name = self._item.get_name() or "unknown"
        label = capitalize_first(name)
        self.children[1].set_label(label)

    def destroy(self) -> None:
        for child in self.children:
            self.remove(child)
        self.click_gesture.disconnect(self.gesture_conn)
        self.remove_controller(self.click_gesture)
        self.quit_btn.disconnect(self.quit_conn)
        self._item.unwatch(self.handler_id)


class TrayBox(gtk.ScrolledWindow):
    def __init__(self) -> None:
        self.box = gtk.Box(
            orientation=gtk.Orientation.VERTICAL
        )
        self.list = gtk.Box(
            orientation=gtk.Orientation.VERTICAL
        )
        self.no_items_label = gtk.Revealer(
            child=gtk.Label(label="There isn't any tray items"),
            transition_duration=250,
            transition_type=gtk.RevealerTransitionType.SLIDE_DOWN,
            css_classes=("no-items",),
        )

        self.box.append(self.no_items_label)
        self.box.append(self.list)

        self.items: dict[str, TrayItem] = {}
        super().__init__(
            child=self.box,
            css_classes=("tray-widget",),
            vscrollbar_policy=gtk.PolicyType.AUTOMATIC,
            hscrollbar_policy=gtk.PolicyType.NEVER
        )
        self.handler_id = items.watch(self.update_items)
        self.update_items(items.value)
        weakref.finalize(self, lambda: logger.debug("TrayBox finalized"))

    def update_items(self, new_items: dict[str, StatusNotifierItem]) -> None:
        existing_items = set(self.items.keys())
        tray_items = set(new_items.keys())
        for item in tray_items:
            if item not in existing_items:
                tray_widget = TrayItem(items.value[item])
                self.items[item] = tray_widget
                self.list.append(tray_widget)

        for item in existing_items:
            if item not in tray_items:
                self.items[item].destroy()
                self.list.remove(self.items[item])
                del self.items[item]

        self.no_items_label.set_reveal_child(len(self.items) == 0)

    def destroy(self) -> None:
        for key, item in self.items.items():
            item.destroy()
            self.list.remove(item)

        self.box.remove(self.no_items_label)
        self.items.clear()
        self.set_child(None)
        items.unwatch(self.handler_id)


class TrayWindow(widget.LayerWindow):
    def __init__(self, app: gtk.Application) -> None:
        super().__init__(
            app,
            anchors={
                "top": True,
                "right": True
            },
            margins={
                "top": HyprlandVars.gap,
                "right": HyprlandVars.gap
            },
            css_classes=("tray",),
            keymode=layer_shell.KeyboardMode.ON_DEMAND,
            layer=layer_shell.Layer.OVERLAY,
            hide_on_esc=True,
            name="tray",
            height=1,
            width=1,
            setup_popup=True
        )
        self._child: TrayBox | None = None

        weakref.finalize(self, lambda: logger.debug("TrayWindow finalized"))

    def on_show(self) -> None:
        self._child = TrayBox()
        self.set_child(self._child)

    def on_hide(self) -> None:
        if self._child:
            self._child.destroy()
        self.set_child(None)
        self._child = None

    def destroy(self) -> None:
        super().destroy()
