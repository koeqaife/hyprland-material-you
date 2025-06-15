from repository import gio, glib
from utils.logger import logger
import typing as t
from utils.service import Service, Signals


session_bus = gio.bus_get_sync(gio.BusType.SESSION, None)
system_bus = gio.bus_get_sync(gio.BusType.SYSTEM, None)
dbus_proxy = gio.DBusProxy.new_sync(
    session_bus,
    gio.DBusProxyFlags.NONE,
    None,
    "org.freedesktop.DBus",
    "/org/freedesktop/DBus",
    "org.freedesktop.DBus",
    None
)
name_owner_changed = Signals(True)


def on_name_owner_changed(
    connection: gio.DBusConnection,
    sender_name: str,
    object_path: str,
    interface_name: str,
    signal_name: str,
    parameters: glib.Variant
) -> None:
    name, old_owner, new_owner = parameters.unpack()
    logger.debug(
        "NameOwnerChanged: %s, '%s' -> '%s'",
        name, old_owner, new_owner
    )
    name_owner_changed.notify(
        "notify",
        name, old_owner, new_owner
    )


def subscribe_signals(connection: gio.DBusConnection) -> int:
    return connection.signal_subscribe(
        "org.freedesktop.DBus",
        "org.freedesktop.DBus",
        "NameOwnerChanged",
        None,
        None,
        gio.DBusSignalFlags.NONE,
        on_name_owner_changed
    )


def cache_proxy_properties(
    conn: gio.DBusConnection,
    proxy: gio.DBusProxy,
    changed: list[str] | None = None,
    callback: t.Callable[[], None] | None = None
) -> None:
    return conn.call(
        proxy.get_name(),
        proxy.get_object_path(),
        "org.freedesktop.DBus.Properties",
        "GetAll",
        glib.Variant("(s)", [proxy.get_interface_name()]),
        glib.VariantType("(a{sv})"),
        gio.DBusCallFlags.NONE,
        -1,
        None,
        lambda _, result: cache_proxy_properties_finish(
            conn, proxy, result, changed, callback
        ),
    )


def cache_proxy_properties_finish(
    conn: gio.DBusConnection,
    proxy: gio.DBusProxy,
    result: gio.AsyncResult,
    changed: list[str] | None = None,
    callback: t.Callable[..., None] | None = None
) -> None:
    try:
        props_var: glib.Variant = conn.call_finish(result)
        if not props_var:
            raise RuntimeError("Can't get the properties variant")
    except Exception as e:
        return logger.debug("Can't update properties for player: %s", e)

    def unpack_properties(
        variant: glib.Variant
    ) -> dict[str, glib.Variant]:
        res: dict[str, glib.Variant] = {}
        variant = variant.get_child_value(0)
        if variant.get_type_string().startswith("a{"):
            for i in range(variant.n_children()):
                v = variant.get_child_value(i)
                res[v.get_child_value(0).unpack()] = v.get_child_value(1)
        return res

    props = unpack_properties(props_var)

    if changed is not None:
        for prop_name in changed:
            prop_value = props.get(prop_name)
            if prop_value is not None:
                proxy.set_cached_property(
                    prop_name, prop_value.get_variant()
                )
    else:
        for prop_name, prop_value in props.items():
            proxy.set_cached_property(
                prop_name, prop_value.get_variant()
            )

    if callback:
        callback(changed)


class DBusService(Service):
    def start(self) -> None:
        subscribe_signals(session_bus)
