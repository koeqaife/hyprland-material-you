from repository import gtk
from src.modules.settings.base import SettingsDropdownRow, DropdownItem
from src.modules.settings.base import SettingsTextRow
from src.modules.settings.base import SettingsBoolRow
from src.modules.settings.base import Hint
from src.modules.settings.base import Category
from src.modules.settings.base import int_kwargs, float_kwargs


class InputPage(gtk.ScrolledWindow):
    __gtype_name__ = "SettingsInputPage"

    def __init__(self) -> None:
        self.box = gtk.Box(
            css_classes=("page-box",),
            orientation=gtk.Orientation.VERTICAL
        )
        super().__init__(
            css_classes=("input-page", "settings-page",),
            child=self.box,
            hscrollbar_policy=gtk.PolicyType.NEVER
        )
        self.box_children = (
            Category("Keyboard"),
            SettingsTextRow(
                "Keyboard model",
                "Specifies the physical model of the keyboard",
                "input.kb_model",
                max_width_chars=12
            ),
            SettingsTextRow(
                "Keyboard layouts",
                "List of active keyboard layouts (e.g., us, ru)",
                "input.kb_layout",
                max_width_chars=12
            ),
            SettingsTextRow(
                "Keyboard variant",
                "Optional layout variant for the selected layout",
                "input.kb_variant",
                max_width_chars=12
            ),
            SettingsTextRow(
                "Keyboard options",
                "XKB options like key behavior and modifier tweaks",
                "input.kb_options",
                max_width_chars=12
            ),
            SettingsTextRow(
                "Keyboard rules",
                "Name of the XKB ruleset",
                "input.kb_rules",
                max_width_chars=12
            ),
            SettingsDropdownRow(
                "Change layout keybind",
                "Combination used to switch between layouts",
                "input.change_layout",
                items=[
                    DropdownItem("", "None"),
                    DropdownItem("grp:shift_caps_toggle", "Shift+Caps Lock"),
                    DropdownItem("grp:alt_caps_toggle", "Alt+Caps Lock"),
                    DropdownItem("grp:ctrl_shift_toggle", "Ctrl+Shift"),
                    DropdownItem("grp:ctrl_alt_toggle", "Alt+Ctrl"),
                    DropdownItem("grp:alt_shift_toggle", "Alt+Shift"),
                    DropdownItem("grp:alt_space_toggle", "Alt+Space"),
                    DropdownItem("grp:win_space_toggle", "Win+Space"),
                    DropdownItem("grp:ctrl_space_toggle", "Ctrl+Space")
                ]
            ),
            SettingsBoolRow(
                "Numlock by default",
                "Enable Num Lock on startup",
                "input.numlock_by_default"
            ),
            SettingsBoolRow(
                "Use keybinds by current layout",
                "Match keybinds to current keyboard layout symbols",
                "input.resolve_binds_by_sym"
            ),
            SettingsTextRow(
                "Key repeat rate",
                "Repeats per second for held keys",
                "input.repeat_rate",
                max_width_chars=6,
                **int_kwargs
            ),
            SettingsTextRow(
                "Key repeat delay",
                "Delay before key repeats, in ms",
                "input.repeat_delay",
                max_width_chars=6,
                **int_kwargs
            ),

            Category("Mouse & Pointer"),
            SettingsTextRow(
                "Mouse sensitivity",
                "Cursor speed adjustment",
                "input.sensitivity",
                max_width_chars=6,
                **float_kwargs
            ),
            SettingsDropdownRow(
                "Pointer acceleration profile",
                "How your cursor accelerates with movement",
                "input.accel_profile",
                items=[
                    DropdownItem("", "Default"),
                    DropdownItem(
                        "adaptive", "Adaptive",
                        "Acceleration based on speed"
                    ),
                    DropdownItem(
                        "flat", "Flat",
                        "Constant acceleration"
                    )
                ]
            ),
            SettingsBoolRow(
                "Force no acceleration",
                "Disable pointer acceleration completely",
                "input.force_no_accel"
            ),
            SettingsBoolRow(
                "Left handed",
                "Swap mouse buttons for left-handed use",
                "input.left_handed"
            ),
            SettingsDropdownRow(
                "Scroll method",
                "Choose how scrolling is performed",
                "input.scroll_method",
                items=[
                    DropdownItem("", "Default"),
                    DropdownItem(
                        "2fg", "Two-fingers",
                        "Two-finger scroll"
                    ),
                    DropdownItem(
                        "edge", "Edge",
                        "Edge scroll"
                    ),
                    DropdownItem(
                        "on_button_down", "On button",
                        "Scroll while button held"
                    ),
                    DropdownItem(
                        "no_scroll", "Disable",
                        "Disable scrolling"
                    )
                ]
            ),
            SettingsBoolRow(
                "Natural scrolling",
                "Invert scroll direction for intuitive movement",
                "input.natural_scroll",
            ),
            SettingsDropdownRow(
                "Focus mode",
                "Controls window focus behavior on mouse move or click",
                "input.follow_mouse",
                items=[
                    DropdownItem(
                        0, "Standard",
                        "Focus changes only when clicked on window"
                    ),
                    DropdownItem(
                        1, "Follow",
                        "Focus always changes to window under cursor"
                    ),
                    DropdownItem(
                        2, "Click",
                        "Click sets keyboard focus to window"
                    ),
                    DropdownItem(
                        3, "Separate",
                        "Click doesn't change keyboard focus"
                    )
                ]
            ),
            SettingsTextRow(
                "Focus follow threshold",
                "Cursor distance to change focus (Focus Follow mode)",
                "input.follow_mouse_threshold",
                max_width_chars=4,
                **float_kwargs
            ),
            SettingsDropdownRow(
                "Focus on close",
                "Behavior of focus when you close window",
                "input.focus_on_close",
                items=[
                    DropdownItem(0, "Next window"),
                    DropdownItem(1, "Under cursor")
                ]
            ),
            SettingsBoolRow(
                "Mouse refocus",
                "Change focus on hover only when crossing window boundary",
                "input.mouse_refocus"
            ),
            SettingsDropdownRow(
                "Float switch override focus",
                "Focus behavior when toggling floating windows",
                "input.float_switch_override_focus",
                items=[
                    DropdownItem(
                        0, "Off",
                        "No focus change on mode switch"
                    ),
                    DropdownItem(
                        1, "Tiled-Float",
                        "Focus follows cursor on tiled/floating switch"
                    ),
                    DropdownItem(
                        2, "Plus float",
                        "Also follows cursor on floating switches"
                    )
                ]
            ),

            Category("Touchpad"),
            SettingsBoolRow(
                "Touchpad settings enabled",
                "If disabled hyprland's default settings will be used",
                "input.touchpad.enabled"
            ),
            SettingsBoolRow(
                "Disable while typing",
                "Touchpad won't work when you're typing",
                "input.touchpad.disable_while_typing"
            ),
            SettingsBoolRow(
                "Natural scrolling",
                "Invert touchpad scroll direction for intuitive movement",
                "input.touchpad.natural_scroll"
            ),
            SettingsBoolRow(
                "Middle button emulation",
                "Left and right click would be interpreted as a middle click",
                "input.touchpad.middle_button_emulation"
            ),
            SettingsBoolRow(
                "Clickfinger behavior",
                "Map 1-3 finger taps to left, right, and middle click",
                "input.touchpad.clickfinger_behavior"
            ),
            SettingsBoolRow(
                "Tap-to-click",
                "Tap with 1-3 fingers to click left, right, or middle button",
                "input.touchpad.tap_to_click"
            ),
            SettingsBoolRow(
                "Tap-to-drag",
                "Enable dragging by tapping and holding",
                "input.touchpad.tap_and_drag"
            ),
            SettingsBoolRow(
                "Flip X",
                "Reverse horizontal movement direction",
                "input.touchpad.flip_x"
            ),
            SettingsBoolRow(
                "Flip Y",
                "Reverse vertical movement direction",
                "input.touchpad.flip_y"
            ),
            SettingsTextRow(
                "Scroll factor",
                "Multiplier applied to the amount of scroll movement",
                "input.touchpad.scroll_factor",
                **float_kwargs,
                max_width_chars=4
            ),
            SettingsDropdownRow(
                "Tap button map",
                "Assign buttons to fingers taps",
                "input.touchpad.tap_button_map",
                items=[
                    DropdownItem(
                        "lrm", "LRM",
                        "Left, Right, Middle (default)"
                    ),
                    DropdownItem(
                        "lmr", "LMR",
                        "Left, Middle, Right"
                    )
                ]
            ),
            Hint(
                "Check /usr/share/X11/xkb/rules/base.lst " +
                "for model, variant and options"
            )
        )
        for child in self.box_children:
            self.box.append(child)

    def destroy(self) -> None:
        for child in self.box_children:
            child.destroy()
