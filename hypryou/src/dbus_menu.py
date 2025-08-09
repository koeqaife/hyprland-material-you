import time
import weakref
from repository import gtk, glib, gio, gobject
from utils.logger import logger
import typing as t


class DBusMenuPopover(gtk.PopoverMenu):
    __gtype_name__ = "DBusMenuPopover"
    IFACE = "com.canonical.dbusmenu"

    def __init__(self, bus_name: str, obj_path: str) -> None:
        super().__init__(
            has_arrow=False
        )
        self.bus_name = bus_name
        self.obj_path = obj_path
        self.conn: gio.DBusConnection = gio.bus_get_sync(
            gio.BusType.SESSION, None
        )
        self._action_group: gio.SimpleActionGroup = gio.SimpleActionGroup()
        self.insert_action_group("dbusmenu", self._action_group)
        self._id_to_action: dict[int, str] = {}
        self._signal_subs: list[int] = []
        self._menu_revision = 0
        self._menu_id = 0
        self._layout_signature: str | None = None
        self._handlers: dict[gobject.Object, int] = {}
        self._subscribe_signals()
        self._request_layout()
        if __debug__:
            weakref.finalize(
                self, lambda: logger.debug("DBusMenuPopover finalized")
            )

    @staticmethod
    def create_wrapper(
        func: t.Callable[..., None]
    ) -> t.Callable[..., None]:
        weak_method = weakref.WeakMethod(func)

        def wrapper(*args: t.Any, **kwargs: t.Any) -> None:
            method = weak_method()
            if callable(method):
                method(*args, **kwargs)

        return wrapper

    def _subscribe_signals(self) -> None:

        subs = [
            (
                "LayoutUpdated",
                self.create_wrapper(self._on_layout_updated)
            ),
            (
                "ItemsPropertiesUpdated",
                self.create_wrapper(self._on_items_props_updated)
            ),
            (
                "ItemPropertiesUpdated",
                self.create_wrapper(self._on_items_props_updated)
            ),
        ]
        for sig_name, handler in subs:
            sub = self.conn.signal_subscribe(
                None,
                self.IFACE,
                sig_name,
                self.obj_path,
                None,
                gio.DBusSignalFlags.NONE,
                handler,
                None,
            )
            self._signal_subs.append(sub)

    def _request_layout(self) -> None:
        props = [
            "label",
            "enabled",
            "visible",
            "type",
            "toggle-type",
            "toggle-state",
            "toggle-group",
            "icon-name",
        ]
        self.conn.call(
            self.bus_name,
            self.obj_path,
            self.IFACE,
            "GetLayout",
            glib.Variant("(iias)", (0, -1, props)),
            None,
            gio.DBusCallFlags.NO_AUTO_START,
            5000,
            None,
            self._on_get_layout,
            None,
        )

    def _on_get_layout(
        self, conn: gio.DBusConnection, res: gio.AsyncResult, _data: t.Any
    ) -> None:
        try:
            ret = conn.call_finish(res)
            unpacked = ret.unpack()
            if not unpacked:
                self._set_fallback_menu()
                return
            revision = unpacked[0]
            layout = unpacked[1]
            self._menu_revision = int(revision)
            gio_menu = gio.Menu()
            self._id_to_action.clear()
            root_children = self._extract_children_from_layout(layout)
            self._menu_id = layout[0]
            self._build_gio_menu(gio_menu, root_children)

            self.set_menu_model(gio_menu)
        except Exception as exc:
            logger.exception("Couldn't get layout", exc_info=exc)
            self._set_fallback_menu()

    def _extract_children_from_layout(
        self, layout: tuple[int, int, list[tuple[int, dict[str, str]]]]
    ) -> list[tuple[int, dict[str, str]]]:
        return list(layout[2])

    def _build_gio_menu(
        self,
        gio_menu: gio.Menu,
        children: list[tuple[int, dict[str, str], dict[str, str]]]
    ) -> None:
        for node in children:
            try:
                node_id, props, sub_children = node
            except Exception as e:
                logger.exception(e)
                continue

            if not props.get("visible", True):
                continue

            item_type = props.get("type", "normal")
            label = props.get("label", "")

            if item_type == "separator":
                continue

            if sub_children:
                submenu = gio.Menu()
                self._build_gio_menu(submenu, sub_children)
                gio_menu.append_submenu(label or "", submenu)
                continue

            action_name = self._register_action(node_id, props)
            gio_menu.append(label or "", f"dbusmenu.{action_name}")

    def _register_action(self, node_id: int, props: dict[str, t.Any]) -> str:
        if node_id in self._id_to_action:
            return self._id_to_action[node_id]
        name = f"action{node_id}"
        act = gio.SimpleAction.new(name, None)
        self._handlers[act] = act.connect(
            "activate",
            self.create_wrapper(self._on_activate),
            node_id
        )
        self._action_group.add_action(act)
        self._id_to_action[node_id] = name
        if not props.get("enabled", True):
            act.set_enabled(False)
        return name

    def _on_activate(
        self, action: gio.SimpleAction, _param: glib.Variant, node_id: int
    ) -> None:
        self._send_event(node_id, "clicked")

    def _send_event(
        self,
        item_id: int,
        event_id: str,
        data: glib.Variant | None = None,
    ) -> None:
        if data is None:
            data = glib.Variant("s", "")
        timestamp = int(time.time())
        self.conn.call(
            self.bus_name,
            self.obj_path,
            self.IFACE,
            "Event",
            glib.Variant("(isvu)", (item_id, event_id, data, timestamp)),
            None,
            gio.DBusCallFlags.NO_AUTO_START,
            -1,
            None,
            None
        )

    def popup(self) -> None:
        if __debug__:
            logger.debug("DBusMenu popup")
        try:
            self.conn.call(
                self.bus_name,
                self.obj_path,
                self.IFACE,
                "AboutToShow",
                glib.Variant("(i)", (self._menu_id,)),
                None,
                gio.DBusCallFlags.NO_AUTO_START,
                1500,
                None
            )
        except glib.Error:
            pass
        return super().popup()

    def _on_layout_updated(
        self,
        conn: gio.DBusConnection,
        sender: str,
        path: str,
        iface: str,
        signal: str,
        params: glib.Variant,
        user_data: t.Any,
    ) -> None:
        try:
            rev = params.unpack()[0]
        except ValueError:
            rev = 0
        if rev != self._menu_revision:
            self._request_layout()

    def _on_items_props_updated(
        self,
        conn: gio.DBusConnection,
        sender: str,
        path: str,
        iface: str,
        signal: str,
        params: glib.Variant,
        user_data: t.Any,
    ) -> None:
        try:
            maybe = params.unpack()
            if not maybe:
                return
            first = maybe[0]
            if isinstance(first, (list, tuple)) and len(first) >= 1:
                items = [it[0] for it in first]
                if items:
                    self._request_layout()
                    return
        except Exception as e:
            logger.exception(e)
        try:
            item_id, props = params.unpack()
        except Exception as e:
            logger.exception(e)
            return
        action_name = self._id_to_action.get(item_id)
        if not action_name:
            return

    def _set_fallback_menu(self) -> None:
        fallback = gio.Menu()
        fallback.append("(empty)", None)
        self.set_menu_model(fallback)

    def destroy(self) -> None:
        for sub in self._signal_subs:
            self.conn.signal_unsubscribe(sub)
        self._signal_subs.clear()

        try:
            for object, handler in self._handlers.items():
                object.disconnect(handler)
        except Exception as e:
            logger.exception(e)

        self._id_to_action.clear()
        self.set_menu_model(None)
