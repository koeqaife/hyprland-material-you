import src.widget as widget
from utils import toggle_css_class
from utils.logger import logger
from repository import gtk, layer_shell, wp, pango, gio, gdk
from config import HyprlandVars
from src.services.audio import ICON_THRESHOLDS
import src.services.audio as audio
import typing as t
import weakref
from utils.ref import Ref


type NodeItem = "EndpointItem | StreamItem"
type CreatorCallback = t.Callable[[wp.Node], NodeItem]


class EndpointIcons(t.NamedTuple):
    muted: str
    low: str
    medium: str
    high: str


class StackPage(t.NamedTuple):
    id: str
    label: str
    icon: str
    tooltip: str
    ref: Ref[set[wp.Node]]
    constructor: CreatorCallback


class EndpointItem(gtk.Box):
    __gtype_name__ = "EndpointItem"

    def __init__(
        self,
        node: wp.Node | wp.Endpoint,
        icons: EndpointIcons
    ) -> None:
        if not isinstance(node, wp.Endpoint):
            raise TypeError
        self.icons = icons
        super().__init__(
            valign=gtk.Align.START,
            hexpand=True,
            css_classes=("audio-item",),
            orientation=gtk.Orientation.VERTICAL
        )
        self.node = node
        self.info_box = gtk.Box(
            css_classes=("info-box",),
            hexpand=True
        )
        self.icon = widget.Icon("")
        self.label = gtk.Label(
            label=self.node.get_description() or self.node.get_name(),
            css_classes=("label",),
            tooltip_text=self.node.get_name(),
            hexpand=True,
            halign=gtk.Align.START,
            ellipsize=pango.EllipsizeMode.END
        )
        self.percent = gtk.Label(
            label="50%",
            css_classes=("percent",),
            halign=gtk.Align.END
        )
        self.info_box.append(self.icon)
        self.info_box.append(self.label)
        self.info_box.append(self.percent)

        self.scale = gtk.Scale.new_with_range(
            gtk.Orientation.HORIZONTAL,
            0, 100, 1
        )
        self.scale.set_hexpand(True)
        self.scale_handler = self.scale.connect(
            "value-changed", self.scale_changed
        )

        self.append(self.info_box)
        self.append(self.scale)

        self.volume_handler = self.node.connect(
            "notify::volume",
            self.update_scale_value
        )
        self.muted_handler = self.node.connect(
            "notify::mute",
            self.on_muted
        )
        self.is_default_handler = self.node.connect(
            "notify::is-default",
            self.on_default
        )

        self.click_gesture = gtk.GestureClick.new()
        self.click_gesture.set_button(gdk.BUTTON_SECONDARY)
        self.gesture_conn = (
            self.click_gesture.connect("released", self.on_click_released)
        )
        self.add_controller(self.click_gesture)

        self.menu = gio.Menu()
        self.popover = gtk.PopoverMenu()
        self.popover.set_parent(self)
        self.popover.set_has_arrow(False)
        self.update_menu()

        self.install_action("set_default", None, self.set_default)
        self.install_action("mute", None, self.toggle_mute)

        self.update_scale_value()
        self.on_muted()
        self.on_default()

    @staticmethod
    def set_default(self: "EndpointItem", *args: t.Any) -> None:
        self.node.set_is_default(True)
        self.update_menu()

    @staticmethod
    def toggle_mute(self: "EndpointItem", *args: t.Any) -> None:
        self.node.set_mute(not self.node.get_mute())
        self.update_menu()

    def update_menu(self, *args: t.Any) -> None:
        self.menu.remove_all()
        if not self.node.get_is_default():
            self.menu.append("Set as default", "set_default")
        else:
            # NOTE: IDK
            self.menu.append("Is default", "is__default")
        self.menu.append(
            "Unmute" if self.node.get_mute() else "Mute",
            "mute"
        )
        self.popover.set_menu_model(self.menu)

    def on_click_released(
        self,
        gesture: gtk.GestureClick,
        n_press: int,
        x: int,
        y: int
    ) -> bool:
        button = gesture.get_current_button()
        if button != gdk.BUTTON_SECONDARY:
            return False

        rect = gdk.Rectangle()
        rect.x = x
        rect.y = y
        self.popover.set_pointing_to(rect)
        self.popover.popup()
        return True

    def on_default(self, *args: t.Any) -> None:
        toggle_css_class(self, "is-default", self.node.get_is_default())
        self.update_icon()
        self.update_menu()

    def on_muted(self, *args: t.Any) -> None:
        toggle_css_class(self, "muted", self.node.get_mute())
        self.update_icon()
        self.update_menu()

    def get_icon(self, volume: float) -> str:
        for i in range(len(ICON_THRESHOLDS) - 1, -1, -1):
            if volume >= ICON_THRESHOLDS[i]:
                return self.icons[i]
        return self.icons[0]

    def update_icon(self, *args: t.Any) -> None:
        if self.node.get_mute():
            self.icon.set_label(self.icons[0])
        else:
            scale_value = self.scale.get_value()
            self.icon.set_label(self.get_icon(scale_value))

    def update_percent(self) -> None:
        scale_value = self.scale.get_value()
        self.percent.set_label(f"{round(scale_value)}%")
        self.update_icon()

    def scale_changed(self, *args: t.Any) -> None:
        scale_value = self.scale.get_value()
        self.node.set_volume(scale_value / 100)
        self.update_percent()

    def update_scale_value(self, *args: t.Any) -> None:
        value = self.node.get_volume() * 100
        self.scale.handler_block(self.scale_handler)
        self.scale.set_value(value)
        self.scale.handler_unblock(self.scale_handler)
        self.update_percent()

    def destroy(self) -> None:
        self.node.disconnect(self.muted_handler)
        self.node.disconnect(self.volume_handler)
        self.node.disconnect(self.is_default_handler)
        self.scale.disconnect(self.scale_handler)
        self.click_gesture.disconnect(self.gesture_conn)
        self.remove_controller(self.click_gesture)


class StreamItem(gtk.Box):
    __gtype_name__ = "StreamItem"

    def __init__(
        self,
        node: wp.Node | wp.Stream
    ) -> None:
        if not isinstance(node, wp.Stream):
            raise TypeError
        super().__init__(
            valign=gtk.Align.START,
            hexpand=True,
            css_classes=("audio-item",),
            orientation=gtk.Orientation.VERTICAL
        )
        self.node = node
        self.info_box = gtk.Box(
            css_classes=("info-box",),
            hexpand=True
        )
        self.icon = gtk.Image(
            icon_name=node.get_icon() or "image-missing",
        )
        is_muted = "" if not self.node.get_mute() else "Muted: "
        self.name = self.node.get_description() or self.node.get_name()
        self.label = gtk.Label(
            label=f"{is_muted}{self.name}",
            css_classes=("label",),
            tooltip_text=self.node.get_name(),
            hexpand=True,
            halign=gtk.Align.START,
            ellipsize=pango.EllipsizeMode.END
        )
        self.percent = gtk.Label(
            label="50%",
            css_classes=("percent",),
            halign=gtk.Align.END
        )
        self.info_box.append(self.icon)
        self.info_box.append(self.label)
        self.info_box.append(self.percent)

        self.scale = gtk.Scale.new_with_range(
            gtk.Orientation.HORIZONTAL,
            0, 100, 1
        )
        self.scale.set_hexpand(True)
        self.scale_handler = self.scale.connect(
            "value-changed", self.scale_changed
        )

        self.append(self.info_box)
        self.append(self.scale)

        self.volume_handler = self.node.connect(
            "notify::volume",
            self.update_scale_value
        )
        self.muted_handler = self.node.connect(
            "notify::mute",
            self.on_muted
        )

        self.click_gesture = gtk.GestureClick.new()
        self.click_gesture.set_button(gdk.BUTTON_SECONDARY)
        self.gesture_conn = (
            self.click_gesture.connect("released", self.on_click_released)
        )
        self.add_controller(self.click_gesture)

        self.update_scale_value()
        self.on_muted()

    def on_click_released(
        self,
        gesture: gtk.GestureClick,
        n_press: int,
        x: int,
        y: int
    ) -> bool:
        button = gesture.get_current_button()
        if button != gdk.BUTTON_SECONDARY:
            return False
        self.node.set_mute(not self.node.get_mute())
        return True

    def on_muted(self, *args: t.Any) -> None:
        toggle_css_class(self, "muted", self.node.get_mute())
        is_muted = "" if not self.node.get_mute() else "Muted: "
        self.label.set_label(f"{is_muted}{self.name}")

    def update_percent(self) -> None:
        scale_value = self.scale.get_value()
        self.percent.set_label(f"{round(scale_value)}%")

    def scale_changed(self, *args: t.Any) -> None:
        scale_value = self.scale.get_value()
        self.node.set_volume(scale_value / 100)
        self.update_percent()

    def update_scale_value(self, *args: t.Any) -> None:
        value = self.node.get_volume() * 100
        self.scale.handler_block(self.scale_handler)
        self.scale.set_value(value)
        self.scale.handler_unblock(self.scale_handler)
        self.update_percent()

    def destroy(self) -> None:
        self.node.disconnect(self.muted_handler)
        self.node.disconnect(self.volume_handler)
        self.scale.disconnect(self.scale_handler)


class NodesList(gtk.ScrolledWindow):
    __gtype_name__ = "NodesList"

    def __init__(
        self,
        ref: Ref[set[wp.Node]],
        constructor: CreatorCallback
    ) -> None:
        self.constructor = constructor
        self.box = gtk.Box(
            orientation=gtk.Orientation.VERTICAL
        )
        self.list = gtk.Box(
            orientation=gtk.Orientation.VERTICAL
        )

        self.box.append(self.list)

        self.items: dict[wp.Node, NodeItem] = {}
        super().__init__(
            child=self.box,
            css_classes=("audio-page",),
            vscrollbar_policy=gtk.PolicyType.NEVER,
            hscrollbar_policy=gtk.PolicyType.NEVER
        )
        if __debug__:
            weakref.finalize(
                self,
                lambda: logger.debug("NodesList finalized")
            )
        self.with_min_height: bool | None = None

        self._ref = ref
        self.handler = ref.watch(self.update_items)
        self.update_items(ref.value)

    def update_items(
        self,
        items: set[wp.Node]
    ) -> None:
        existing_nodes = set(self.items.keys())
        new_nodes = set(items)

        for node in existing_nodes:
            if node not in new_nodes:
                item = self.items.pop(node)
                self.list.remove(item)

        for node in new_nodes:
            if node not in existing_nodes:
                item = self.constructor(node)
                self.items[node] = item
                self.list.append(self.items[node])

        if len(self.items) > 5 and not self.with_min_height:
            self.set_policy(
                vscrollbar_policy=gtk.PolicyType.ALWAYS,
                hscrollbar_policy=gtk.PolicyType.NEVER
            )
            toggle_css_class(self, "with-min-height", True)
        elif self.with_min_height:
            self.set_policy(
                vscrollbar_policy=gtk.PolicyType.NEVER,
                hscrollbar_policy=gtk.PolicyType.NEVER
            )
            toggle_css_class(self, "with-min-height", False)

    def destroy(self) -> None:
        for key, item in self.items.items():
            item.destroy()
            self.list.remove(item)
        self.items.clear()
        self.set_child(None)


class AudioBoxTemplate(gtk.Box):
    __gtype_name__ = "AudioBoxTemplate"
    pages: list[StackPage] = []

    def __init__(self) -> None:
        super().__init__(
            orientation=gtk.Orientation.VERTICAL,
            css_classes=("audio-box",)
        )

        self._last_active: widget.StackButton | None = None
        self.current_page = self.pages[0].id
        self.buttons: dict[str, widget.StackButton] = {}
        self.page_widgets: list[NodesList] = []
        self.buttons_box = gtk.Box(
            css_classes=("buttons-box",),
            homogeneous=True
        )
        self.stack = gtk.Stack(
            css_classes=("audio-stack",),
            transition_type=gtk.StackTransitionType.CROSSFADE,
            transition_duration=250
        )
        for page in self.pages:
            button = widget.StackButton(
                page.id, page.label, page.icon,
                self.change_page, page.tooltip
            )
            self.buttons[page.id] = button
            self.buttons_box.append(button)

            page_widget = NodesList(page.ref, page.constructor)
            self.stack.add_named(
                page_widget,
                page.id
            )
            self.page_widgets.append(page_widget)

        self.append(self.buttons_box)
        self.append(self.stack)
        self.update_active_button()

    def update_active_button(self) -> None:
        new_active = self.buttons[self.current_page]
        if new_active is not self._last_active:
            if self._last_active is not None:
                toggle_css_class(self._last_active, "active", False)
            toggle_css_class(new_active, "active", True)
            self._last_active = new_active

    def change_page(self, to: str) -> None:
        self.stack.set_visible_child_name(to)
        self.current_page = to
        self.update_active_button()

    def destroy(self) -> None:
        for button in self.buttons.values():
            button.destroy()
        for page in self.page_widgets:
            page.destroy()


class SpeakersBox(AudioBoxTemplate):
    __gtype_name__ = "SpeakersBox"
    pages = [
        StackPage(
            "speakers",
            "Speakers",
            "volume_up",
            "Speakers",
            t.cast(Ref[set[wp.Node]], audio.speakers),
            lambda node: EndpointItem(
                node,
                EndpointIcons(
                    "volume_off", "volume_mute",
                    "volume_down", "volume_up"
                )
            )
        ),
        StackPage(
            "playback",
            "Playback",
            "apps",
            "Apps/plugins that play sound",
            t.cast(Ref[set[wp.Node]], audio.streams),
            lambda node: StreamItem(node)
        )
    ]


class MicsBox(AudioBoxTemplate):
    __gtype_name__ = "MicsBox"
    pages = [
        StackPage(
            "mics",
            "Mics",
            "mic",
            "Microphones",
            t.cast(Ref[set[wp.Node]], audio.microphones),
            lambda node: EndpointItem(
                node,
                EndpointIcons(
                    "mic_off", "mic",
                    "mic", "mic"
                )
            )
        ),
        StackPage(
            "recorders",
            "Recorders",
            "mic_double",
            "Apps that use your mic",
            t.cast(Ref[set[wp.Node]], audio.recorders),
            lambda node: StreamItem(node)
        ),
    ]


class AudioWindow(widget.LayerWindow):
    __gtype_name__ = "AudioWindow"

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
            setup_popup=True,
            hide_on_esc=True,
            keymode=layer_shell.KeyboardMode.ON_DEMAND,
            name="audio",
            css_classes=("audio",)
        )
        self._child: SpeakersBox | None = None

    def on_show(self) -> None:
        self._child = SpeakersBox()
        self.set_child(self._child)

    def on_hide(self) -> None:
        if self._child:
            self._child.destroy()
        self.set_child(None)
        self._child = None


class MicsWindow(widget.LayerWindow):
    __gtype_name__ = "MicsWindow"

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
            setup_popup=True,
            hide_on_esc=True,
            keymode=layer_shell.KeyboardMode.ON_DEMAND,
            layer=layer_shell.Layer.OVERLAY,
            name="mics",
            css_classes=("audio",)
        )
        self._child: MicsBox | None = None

    def on_show(self) -> None:
        self._child = MicsBox()
        self.set_child(self._child)

    def on_hide(self) -> None:
        if self._child:
            self._child.destroy()
        self.set_child(None)
        self._child = None
