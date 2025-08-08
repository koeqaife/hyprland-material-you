import weakref
from repository import gtk, glib, gio, gobject
from utils.logger import logger
import typing as t


class DBusMenuPopover(gtk.PopoverMenu):
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
        self._radio_groups: dict[str, list[int]] = {}
        self._signal_subs: list[int] = []
        self._timers: list[int] = []
        self._menu_revision: int = 0
        self._layout_signature: str | None = None
        self._about_to_show_retry: bool = False
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
        candidates: list[tuple[str, t.Tuple[t.Any, ...]]] = [
            ("(iiias)", (0, 0, -1, props)),
            ("(iias)", (0, -1, props)),
            ("(iias)", (0, 0, props)),
            ("(iias)", (0, 0, [])),
        ]
        chosen: tuple[str, t.Tuple[t.Any, ...]] | None = None
        last_exc: Exception | None = None
        for sig, args in candidates:
            try:
                self.conn.call_sync(
                    self.bus_name,
                    self.obj_path,
                    self.IFACE,
                    "GetLayout",
                    glib.Variant(sig, args),
                    None,
                    gio.DBusCallFlags.NO_AUTO_START,
                    2000,
                    None,
                )
                chosen = (sig, args)
                break
            except glib.Error as exc:
                last_exc = exc
                txt = str(exc)
                if "InvalidArgs" in txt:
                    continue
                if "error occurred in GetLayout" in txt:
                    if self._try_about_to_show(0):
                        try:
                            self.conn.call_sync(
                                self.bus_name,
                                self.obj_path,
                                self.IFACE,
                                "GetLayout",
                                glib.Variant(sig, args),
                                None,
                                gio.DBusCallFlags.NO_AUTO_START,
                                2000,
                                None,
                            )
                            chosen = (sig, args)
                            break
                        except glib.Error as exc2:
                            last_exc = exc2
                            continue
                continue
        if chosen is None:
            logger.error(
                "Couldn't determine GetLayout signature: %s", last_exc
            )
            return
        self._layout_signature = chosen[0]
        self.conn.call(
            self.bus_name,
            self.obj_path,
            self.IFACE,
            "GetLayout",
            glib.Variant(self._layout_signature, chosen[1]),
            None,
            gio.DBusCallFlags.NO_AUTO_START,
            -1,
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
            layout = unpacked[1] if len(unpacked) > 1 else unpacked[0]
            logger.debug("GetLayout -> revision: %s", revision)
            logger.debug("Layout repr: %s", repr(layout)[:1200])
            self._menu_revision = int(revision)
            gio_menu = gio.Menu()
            self._id_to_action.clear()
            self._radio_groups.clear()
            root_children = self._extract_children_from_layout(layout)
            added = self._build_gio_menu(gio_menu, root_children)
            if added == 0:
                if not self._about_to_show_retry:
                    self._about_to_show_retry = True
                    if self._try_about_to_show(0):
                        t_id = glib.timeout_add(
                            80, self._delayed_request_layout
                        )
                        self._timers.append(t_id)
                        return
                self._set_fallback_menu()
            else:
                self._about_to_show_retry = False
                self.set_menu_model(gio_menu)
        except Exception as exc:
            logger.exception("Couldn't get layout", exc_info=exc)
            self._set_fallback_menu()

    def _delayed_request_layout(self) -> bool:
        self._request_layout()
        return False

    def _extract_children_from_layout(self, layout: t.Any) -> list[t.Any]:
        if (
            isinstance(layout, tuple)
            and len(layout) >= 3
            and isinstance(layout[0], int)
        ):
            maybe_children = layout[2]
            if isinstance(maybe_children, (list, tuple)):
                return list(maybe_children)
        elif isinstance(layout, tuple) and len(layout) == 2:
            inner = layout[1]
            if (
                isinstance(inner, tuple)
                and len(inner) >= 3
                and isinstance(inner[0], int)
            ):
                maybe_children = inner[2]
                if isinstance(maybe_children, (list, tuple)):
                    return list(maybe_children)
        elif isinstance(layout, (list, tuple)):
            for item in layout:
                if (
                    isinstance(item, tuple)
                    and len(item) >= 3
                    and isinstance(item[0], int)
                ):
                    maybe_children = item[2]
                    if isinstance(maybe_children, (list, tuple)):
                        return list(maybe_children)
        return []

    def _build_gio_menu(
        self, gio_menu: gio.Menu, children: list[t.Any]
    ) -> int:
        added = 0
        for node in children:
            try:
                node_id, props, sub_children = node
            except Exception as e:
                logger.exception(e)
                continue
            if props.get("visible", True) is False:
                continue
            item_type = props.get("type", "normal")
            label = props.get("label", "")
            if item_type == "separator":
                section = gio.Menu()
                gio_menu.append_section(None, section)
                continue
            if sub_children:
                submenu = gio.Menu()
                sub_added = self._build_gio_menu(submenu, sub_children)
                if sub_added > 0:
                    gio_menu.append_submenu(label or "", submenu)
                    added += 1
                continue
            toggle_type = props.get("toggle-type", None)
            if toggle_type == "check":
                action_name = self._register_check_action(node_id, props)
                gio_menu.append(label or "", f"dbusmenu.{action_name}")
                added += 1
                continue
            if toggle_type == "radio":
                action_name = self._register_radio_action(node_id, props)
                gio_menu.append(label or "", f"dbusmenu.{action_name}")
                added += 1
                continue
            action_name = self._register_action(node_id, props)
            gio_menu.append(label or "", f"dbusmenu.{action_name}")
            added += 1
        return added

    def _register_action(self, node_id: int, props: dict[str, t.Any]) -> str:
        name = f"action{node_id}"
        if name in self._id_to_action.values():
            return name
        act = gio.SimpleAction.new(name, None)
        self._handlers[act] = act.connect(
            "activate", self._on_activate, node_id
        )
        self._action_group.add_action(act)
        self._id_to_action[node_id] = name
        if not props.get("enabled", True):
            act.set_enabled(False)
        return name

    def _register_check_action(
        self, node_id: int, props: dict[str, t.Any]
    ) -> str:
        name = f"action{node_id}"
        state = bool(props.get("toggle-state", False))
        if name in self._id_to_action.values():
            return name
        act = gio.SimpleAction.new_stateful(
            name, None, glib.Variant("b", state)
        )
        act.connect("activate", self._on_check_activate, node_id)
        self._action_group.add_action(act)
        self._id_to_action[node_id] = name
        if not props.get("enabled", True):
            act.set_enabled(False)
        return name

    def _register_radio_action(
        self, node_id: int, props: dict[str, t.Any]
    ) -> str:
        name = f"action{node_id}"
        group = str(props.get("toggle-group", "default"))
        if group not in self._radio_groups:
            self._radio_groups[group] = []
        self._radio_groups[group].append(node_id)
        state = bool(props.get("toggle-state", False))
        if name in self._id_to_action.values():
            return name
        act = gio.SimpleAction.new_stateful(
            name, None, glib.Variant("b", state)
        )
        act.connect("activate", self._on_radio_activate, (node_id, group))
        self._action_group.add_action(act)
        self._id_to_action[node_id] = name
        if not props.get("enabled", True):
            act.set_enabled(False)
        return name

    def _on_activate(
        self, action: gio.SimpleAction, _param: glib.Variant, node_id: int
    ) -> None:
        self._send_event(node_id, "clicked")

    def _on_check_activate(
        self, action: gio.SimpleAction, _param: glib.Variant, node_id: int
    ) -> None:
        current = action.get_state().get_boolean()
        new_state = not current
        action.set_state(glib.Variant("b", new_state))
        self._send_event(node_id, "clicked", glib.Variant("b", new_state))

    def _on_radio_activate(
        self,
        action: gio.SimpleAction,
        _param: glib.Variant,
        info: tuple[int, str],
    ) -> None:
        node_id, group = info
        for other_id in self._radio_groups.get(group, []):
            if other_id == node_id:
                continue
            other_name = self._id_to_action.get(other_id)
            if not other_name:
                continue
            other_act = self._action_group.lookup_action(other_name)
            if not other_act:
                continue
            other_act.set_state(glib.Variant("b", False))
        action.set_state(glib.Variant("b", True))
        self._send_event(node_id, "clicked", glib.Variant("b", True))

    def _send_event(
        self,
        item_id: int,
        event_id: str,
        data: glib.Variant | None = None,
    ) -> None:
        if data is None:
            data = glib.Variant("s", "")
        timestamp = 0
        try:
            self.conn.call_sync(
                self.bus_name,
                self.obj_path,
                self.IFACE,
                "Event",
                glib.Variant("(isvu)", (item_id, event_id, data, timestamp)),
                None,
                gio.DBusCallFlags.NO_AUTO_START,
                -1,
                None,
            )
        except Exception as e:
            logger.exception(e)

    def _try_about_to_show(self, item_id: int) -> bool:
        try:
            self.conn.call_sync(
                self.bus_name,
                self.obj_path,
                self.IFACE,
                "AboutToShow",
                glib.Variant("(i)", (item_id,)),
                None,
                gio.DBusCallFlags.NO_AUTO_START,
                1500,
                None,
            )
            return True
        except Exception:
            try:
                self.conn.call_sync(
                    self.bus_name,
                    self.obj_path,
                    self.IFACE,
                    "Event",
                    glib.Variant(
                        "(isvu)",
                        (item_id, "AboutToShow", glib.Variant("s", ""), 0)
                    ),
                    None,
                    gio.DBusCallFlags.NO_AUTO_START,
                    1500,
                    None,
                )
                return True
            except Exception as e:
                logger.exception(e)
                return False

    def request_about_to_show_for(self, item_id: int) -> bool:
        return self._try_about_to_show(item_id)

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
        act = self._action_group.lookup_action(action_name)
        if not act:
            return
        if "enabled" in props:
            act.set_enabled(bool(props["enabled"]))
        if "toggle-state" in props:
            st = bool(props["toggle-state"])
            try:
                act.set_state(glib.Variant("b", st))
            except Exception as e:
                logger.exception(e)

    def _set_fallback_menu(self) -> None:
        fallback = gio.Menu()
        try:
            fallback.append("(empty)", None)
            self.set_menu_model(fallback)
        except Exception as e:
            logger.exception(e)
            try:
                self.set_menu_model(None)
            except Exception as e:
                logger.exception(e)

    def destroy(self) -> None:
        for t_id in getattr(self, "_timers", []):
            try:
                glib.source_remove(t_id)
            except Exception as e:
                logger.exception(e)
        try:
            self._timers.clear()
        except Exception as e:
            logger.exception(e)

        for sub in self._signal_subs:
            try:
                self.conn.signal_unsubscribe(sub)
            except Exception as e:
                logger.exception(e)

        self._signal_subs.clear()
        try:
            self.insert_action_group("dbusmenu", None)
        except Exception as e:
            logger.exception(e)

        try:
            for object, handler in self._handlers.items():
                object.disconnect(handler)
        except Exception as e:
            logger.exception(e)

        self._id_to_action.clear()
        self._radio_groups.clear()
        self.set_menu_model(None)
