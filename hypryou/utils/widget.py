from repository import gtk, layer_shell, gdk
from utils.ref import Ref
from utils.logger import logger
import typing as t
import cairo
from math import pi
from config import HyprlandVars

import src.services.state as state


__all__ = [
    "Edges", "LayerWindow"
]

type Edges = t.Literal["top", "bottom", "left", "right"]
type Margins = dict[Edges, int]
type Anchors = dict[Edges, bool]


class LayerWindow(gtk.ApplicationWindow):
    def __init__(
        self,
        application: gtk.Application,
        *,
        width: int = 1,
        height: int = 1,
        layer: layer_shell.Layer = layer_shell.Layer.TOP,
        margins: Margins | None = None,
        anchors: Anchors | None = None,
        exclusive: bool = False,
        monitor: gdk.Monitor | None = None,
        keymode: layer_shell.KeyboardMode | None = None,
        hide_on_esc: bool = False,
        name: str | None = None,
        setup_popup: bool | None = None,
        **kwargs: t.Any
    ) -> None:
        super().__init__(application=application, name=name, **kwargs)
        self.name = name
        self.is_popup = setup_popup
        if width and height:
            self.set_default_size(width, height)

        layer_shell.init_for_window(self)
        layer_shell.set_layer(self, layer)

        if anchors:
            for edge, value in anchors.items():
                assert isinstance(value, bool)
                edge_enum = t.cast(
                    layer_shell.Edge,
                    getattr(layer_shell.Edge, edge.upper())
                )
                layer_shell.set_anchor(self, edge_enum, value)

        if margins:
            for edge, margin in margins.items():
                assert isinstance(margin, int)
                edge_enum = t.cast(
                    layer_shell.Edge,
                    getattr(layer_shell.Edge, edge.upper())
                )
                layer_shell.set_margin(self, edge_enum, margin)

        if exclusive:
            layer_shell.auto_exclusive_zone_enable(self)

        if monitor:
            layer_shell.set_monitor(self, monitor)

        if keymode:
            layer_shell.set_keyboard_mode(self, keymode)

        if hide_on_esc:
            self.key_controller = gtk.EventControllerKey()
            self.key_controller.connect("key-pressed", self.on_key_press)
            self.add_controller(self.key_controller)

        if name:
            layer_shell.set_namespace(self, name)
        else:
            logger.warning(f"No name specified for window: {self}")

        if setup_popup:
            self.window_handler = state.opened_windows.watch(
                f"changed::{self.name}",
                self.update_visible
            )
            self.update_visible(False)

    def on_key_press(
        self,
        controller: gtk.EventControllerKey,
        keyval: int,
        *args: t.Any
    ) -> None:
        if keyval == gdk.KEY_Escape:
            if self.is_popup:
                state.close_window(self.name)
            else:
                self.hide()

    def update_visible(self, is_opened: bool) -> None:
        is_visible = self.get_visible()

        if is_opened and not is_visible:
            self.present()
        elif not is_opened and is_visible:
            self.hide()

    def on_show(self) -> None:
        ...

    def on_hide(self) -> None:
        ...

    def hide(self) -> None:
        super().hide()
        self.on_hide()

    def present(self) -> None:
        super().present()
        self.on_show()

    def destroy(self) -> None:
        if getattr(self, "key_controller", None):
            self.remove_controller(self.key_controller)
        if getattr(self, "window_handler", None):
            state.opened_windows.unwatch(
                f"changed::{self.name}",
                self.window_handler
            )
        super().destroy()


class Icon(gtk.Label):
    def __init__(
        self, icon: str | Ref[str],
        **props: t.Any
    ) -> None:
        super().__init__(**props)
        self.add_css_class("material-icon")
        self.add_css_class("icon")
        self.icon = icon
        if isinstance(icon, str):
            self.set_label(icon)
        elif isinstance(icon, Ref):
            self.set_label(icon.value)
            self.handler_id = icon.watch(self.update)

    def update(self, value: str) -> None:
        self.set_label(value)

    def destroy(self) -> None:
        if isinstance(self.icon, Ref):
            self.icon.unwatch(self.handler_id)


class RoundedCorner(gtk.DrawingArea):
    def __init__(
        self,
        place: str,
        radius: int | None = None,
        **props: t.Any
    ) -> None:
        if radius is None:
            radius = HyprlandVars.gap + HyprlandVars.rounding
        super().__init__(**props)
        self.radius = radius
        self.place = place
        self.set_draw_func(self.on_draw)
        self.set_content_height(radius)
        self.set_content_width(radius)
        self.add_css_class("corner")

    def on_draw(
        self,
        widget: t.Self,
        cr: cairo.Context,  # type: ignore[type-arg]
        width: int,
        height: int
    ) -> None:
        radius = self.radius
        style_context = widget.get_style_context()
        color = style_context.get_color()

        r, g, b, a = color.red, color.green, color.blue, color.alpha

        if self.place == "top-left":
            cr.arc(radius, radius, radius, pi, 1.5 * pi)
            cr.line_to(0, 0)
        elif self.place == "top-right":
            cr.arc(0, radius, radius, 1.5 * pi, 2 * pi)
            cr.line_to(radius, 0)
        elif self.place == "bottom-left":
            cr.arc(radius, 0, radius, 0.5 * pi, pi)
            cr.line_to(0, radius)
        elif self.place == "bottom-right":
            cr.arc(0, 0, radius, 0, 0.5 * pi)
            cr.line_to(radius, radius)

        cr.close_path()
        cr.set_source_rgba(r, g, b, a)
        cr.fill()
