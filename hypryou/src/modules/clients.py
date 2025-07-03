from repository import layer_shell, gtk, gdk, pango
import weakref
import src.widget as widget
from config import HyprlandVars
from utils.logger import logger
from src.services.hyprland import clients, Client
from src.services.hyprland import acquire_clients, release_clients
import src.services.hyprland as hyprland
import typing as t
import asyncio


class ClientItem(gtk.Box):
    __gtype_name__ = "ClientItem"

    def __init__(self, item: Client) -> None:
        super().__init__(
            valign=gtk.Align.START,
            hexpand=True,
            css_classes=("client-item",)
        )
        self._item = item

        self.image = gtk.Image()
        self.title = gtk.Label(
            css_classes=("app-title",),
            ellipsize=pango.EllipsizeMode.END,
            hexpand=True,
            xalign=0
        )
        self.workspace = gtk.Label(
            css_classes=("workspace",),
            label="0"
        )

        self.children = (
            self.image,
            self.title,
            self.workspace
        )
        self.on_changed()
        self.update_image()
        for child in self.children:
            self.append(child)

        self.click_gesture = gtk.GestureClick.new()
        self.click_gesture.set_button(0)
        self.gesture_conn = (
            self.click_gesture.connect("released", self.on_click_released)
        )
        self.add_controller(self.click_gesture)

        self.handler_id = self._item.watch("changed", self.on_changed)

    def on_changed(self, *args: t.Any) -> None:
        self.title.set_label(self._item.title)
        self.set_tooltip_text(self._item.title)
        self.workspace.set_label(str(self._item.workspace_id))

    def on_click_released(
        self,
        gesture: gtk.GestureClick,
        n_press: int,
        x: int,
        y: int
    ) -> None:
        button_number = gesture.get_current_button()
        if button_number == gdk.BUTTON_PRIMARY:
            asyncio.create_task(
                hyprland.client.raw(
                    f"dispatch focuswindow address:{self._item.address}"
                )
            )
        elif button_number == gdk.BUTTON_SECONDARY:
            ...

    def update_image(self) -> None:
        if not self.get_visible():
            return
        image = self.children[0]
        icon = self._item.get_icon()
        if icon is None:
            image.set_from_icon_name("image-missing")
        else:
            image.set_from_paintable(icon)
        image.set_size_request(32, 32)

    def destroy(self) -> None:
        for child in self.children:
            self.remove(child)
        self.click_gesture.disconnect(self.gesture_conn)
        self.remove_controller(self.click_gesture)
        self._item.unwatch(self.handler_id)


class ClientsBox(gtk.ScrolledWindow):
    __gtype_name__ = "ClientsBox"

    def __init__(self) -> None:
        self.box = gtk.Box(
            orientation=gtk.Orientation.VERTICAL
        )
        self.list = gtk.Box(
            orientation=gtk.Orientation.VERTICAL
        )
        self.no_items_label = gtk.Revealer(
            child=gtk.Label(label="There are no open windows."),
            transition_duration=250,
            transition_type=gtk.RevealerTransitionType.SLIDE_DOWN,
            css_classes=("no-items",),
            reveal_child=False
        )

        self.box.append(self.no_items_label)
        self.box.append(self.list)

        self.items: dict[str, ClientItem] = {}
        super().__init__(
            child=self.box,
            css_classes=("clients-box",),
            vscrollbar_policy=gtk.PolicyType.AUTOMATIC,
            hscrollbar_policy=gtk.PolicyType.NEVER
        )
        self.handler_id = clients.watch(self.update_items)
        self.update_items(clients.value)
        if __debug__:
            weakref.finalize(
                self, lambda: logger.debug("ClientsBox finalized")
            )

    def update_items(self, new_items: dict[str, Client]) -> None:
        existing_items = set(self.items.keys())
        clients_items = set(new_items.keys())
        for item in clients_items:
            if item not in existing_items:
                client_widget = ClientItem(clients.value[item])
                self.items[item] = client_widget
                self.list.append(client_widget)

        for item in existing_items:
            if item not in clients_items:
                self.items[item].destroy()
                self.list.remove(self.items[item])
                del self.items[item]

        self.no_items_label.set_reveal_child(len(self.items) == 0)
        self.sort_items()

    def sort_items(self) -> None:
        new_dict = dict(
            sorted(
                self.items.items(),
                key=lambda item: (
                    0 - item[1]._item.workspace_id,
                    item[1]._item.pid,
                    *item[1]._item.at
                )
            )
        )
        self.items = new_dict

        for child in list(self.list):  # type: ignore [call-overload]
            self.list.remove(child)

        for key, _widget in self.items.items():
            self.list.insert_child_after(_widget, None)

    def destroy(self) -> None:
        for key, item in self.items.items():
            item.destroy()
            self.list.remove(item)

        self.box.remove(self.no_items_label)
        self.items.clear()
        self.set_child(None)
        clients.unwatch(self.handler_id)


class ClientsWindow(widget.LayerWindow):
    __gtype_name__ = "ClientsWindow"

    def __init__(self, app: gtk.Application) -> None:
        super().__init__(
            app,
            anchors={
                "top": True,
                "left": True
            },
            margins={
                "top": HyprlandVars.gap,
                "left": HyprlandVars.gap
            },
            css_classes=("clients",),
            keymode=layer_shell.KeyboardMode.ON_DEMAND,
            layer=layer_shell.Layer.OVERLAY,
            hide_on_esc=True,
            name="clients",
            height=1,
            width=1,
            setup_popup=True
        )
        self._child: ClientsBox | None = None
        self.once_handler = -1

        if __debug__:
            weakref.finalize(
                self, lambda: logger.debug("ClientsWindow finalized")
            )

    def update_visible(self, is_opened: bool) -> None:
        is_visible = self.get_visible()

        if is_opened and not is_visible:
            self.once_handler = clients.watch_signal(
                "synced", lambda *_: self.present(), once=True
            )
            acquire_clients()
        elif not is_opened and is_visible:
            self.hide()

    def on_show(self) -> None:
        if not self._child:
            self._child = ClientsBox()
            self.set_child(self._child)

    def on_hide(self) -> None:
        self.remove_handler()
        if self._child:
            self._child.destroy()
            release_clients()
        self.set_child(None)
        self._child = None

    def remove_handler(self) -> None:
        if self.once_handler in clients.handlers_signal("synced"):
            clients.unwatch_signal(self.once_handler)

    def destroy(self) -> None:
        self.remove_handler()
        super().destroy()
