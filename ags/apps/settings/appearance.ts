import { theme, theme_settings, generation_scheme_file } from "variables.ts";
const GLib = imports.gi.GLib;
import Gtk from "gi://Gtk?version=3.0";
import config from "services/configuration.ts";
import { Binding } from "types/service";
import { default_config } from "../../services/configuration";

const ComboBoxText = Widget.subclass<typeof Gtk.ComboBoxText, Gtk.ComboBoxText.ConstructorProperties>(Gtk.ComboBoxText);

const color_schemes = {
    "TonalSpot (Recommended)": "tonalSpot",
    Expressive: "expressive",
    FruitSalad: "fruitSalad",
    Monochrome: "monochrome",
    Rainbow: "rainbow",
    Vibrant: "vibrant",
    Neutral: "neutral",
    Fidelity: "fidelity",
    Content: "content",
    [Symbol.iterator]: function* () {
        const keys = Object.keys(this);
        for (const key of keys) {
            yield { key, value: this[key] };
        }
    }
};

let theme_reload_lock = false;
const color_generator = `${GLib.get_home_dir()}/dotfiles/material-colors/generate.py`;

function isNumeric(str: string) {
    return !isNaN(Number(str)) && isFinite(Number(str));
}

function hueToHex(hue: number): string {
    hue = hue / 360.0;

    let rgb = hlsToRgb(hue, 0.5, 1.0);

    let hexColorStr = `#${toHex(rgb[0] * 255)}${toHex(rgb[1] * 255)}${toHex(rgb[2] * 255)}`;

    return hexColorStr;
}

function hlsToRgb(h: number, l: number, s: number): number[] {
    if (s == 0) {
        return [l, l, l];
    }

    function hue2rgb(p: number, q: number, t: number) {
        if (t < 0) t += 1;
        if (t > 1) t -= 1;
        if (t < 1 / 6) return p + (q - p) * 6 * t;
        if (t < 1 / 2) return q;
        if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
        return p;
    }

    let q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    let p = 2 * l - q;

    let r = hue2rgb(p, q, h + 1 / 3);
    let g = hue2rgb(p, q, h);
    let b = hue2rgb(p, q, h - 1 / 3);

    return [r, g, b];
}

function toHex(value: number) {
    let hex = Math.round(value).toString(16);
    return hex.length == 1 ? "0" + hex : hex;
}

const ReloadTheme = () => {
    let { color, scheme } = theme_settings;
    let _color = color.value;
    let color_to_write = _color;
    if (_color.length > 0 && isNumeric(_color) && Number(_color) >= 0 && Number(_color) <= 360) {
        _color = hueToHex(Number(_color));
        color_to_write = `-${color.value}`;
    }
    if (theme_reload_lock) return;
    function Default() {
        Utils.execAsync(`python -O ${color_generator} -w --color-scheme "${theme.value}" --scheme "${scheme.value}"`)
            .finally(() => {
                theme_reload_lock = false;
            })
            .then(() => {
                Utils.writeFile("none", `${GLib.get_home_dir()}/dotfiles/.settings/custom-color`).catch(print);
            })
            .catch(print);
    }
    theme_reload_lock = true;
    if (_color != "none" && _color.length > 6)
        Utils.execAsync(
            `python -O ${color_generator} --color "${_color}" --color-scheme "${theme.value}" --scheme "${scheme.value}"`
        )
            .finally(() => {
                theme_reload_lock = false;
            })
            .then(() => {
                Utils.writeFile(color_to_write, `${GLib.get_home_dir()}/dotfiles/.settings/custom-color`).catch(print);
            })
            .catch((err) => {
                print(err);
                Default();
            });
    else Default();
};

const DarkTheme = () =>
    Widget.EventBox({
        class_name: "row",
        on_primary_click_release: (self) => {
            self.child.children[1]!.activate();
        },
        child: Widget.Box({
            class_name: "row",
            vpack: "start",
            children: [
                Widget.Box({
                    vertical: true,
                    hexpand: true,
                    vpack: "center",
                    children: [
                        Widget.Label({
                            hpack: "start",
                            class_name: "title",
                            label: "Dark theme"
                        })
                        // Widget.Label({
                        //     hpack: "start",
                        //     class_name: "description",
                        //     label: "Idk"
                        // })
                    ]
                }),
                Widget.Switch({
                    vexpand: false,
                    vpack: "center",
                    hpack: "end",
                    on_activate: (self) => {
                        if (self.active != (theme.value.trim() == "dark")) {
                            Utils.execAsync(
                                `${App.configDir}/scripts/dark-theme.sh --set ${self.state ? "dark" : "light"}`
                            ).catch(print);
                            theme.setValue(self.state ? "dark" : "light");
                        }
                    },
                    state: theme.bind().as((c) => c.trim() == "dark")
                })
            ]
        })
    });

const ThemeColor = () =>
    Widget.EventBox({
        class_name: "row",
        on_primary_click_release: (self) => {
            // self.child.children[1]!.activate()
        },
        child: Widget.Box({
            class_name: "row",
            vpack: "start",
            children: [
                Widget.Box({
                    vertical: true,
                    hexpand: true,
                    vpack: "center",
                    hpack: "start",
                    children: [
                        Widget.Label({
                            hpack: "start",
                            class_name: "title",
                            label: "Color"
                        }),
                        Widget.Label({
                            hpack: "start",
                            class_name: "description",
                            label: "Write HUE or #HEX in color"
                        })
                    ]
                }),
                Widget.Entry({
                    max_length: 7,
                    hpack: "end",
                    css: "border: 2px solid; border-color: transparent;",
                    text: theme_settings.color.value,
                    on_accept: (self) => {
                        theme_settings.color.setValue(self.text!);
                        ReloadTheme();
                    },
                    on_change: (self) => {
                        if (self.text!.length > 6) self.css = `border: 2px solid; border-color: ${self.text!}`;
                        else if (
                            self.text!.length > 0 &&
                            isNumeric(self.text!) &&
                            Number(self.text!) >= 0 &&
                            Number(self.text!) <= 360
                        )
                            self.css = `border: 2px solid; border-color: ${hueToHex(Number(self.text))}`;
                        else self.css = `border: 2px solid; border-color: transparent;`;
                    }
                })
            ]
        })
    });

const ColorScheme = () =>
    Widget.EventBox({
        class_name: "row",
        on_primary_click_release: (self) => {
            // self.child.children[1]!.activate()
        },
        child: Widget.Box({
            class_name: "row",
            vpack: "start",
            children: [
                Widget.Box({
                    vertical: true,
                    hexpand: true,
                    vpack: "center",
                    hpack: "start",
                    children: [
                        Widget.Label({
                            hpack: "start",
                            class_name: "title",
                            label: "Scheme"
                        }),
                        Widget.Label({
                            hpack: "start",
                            class_name: "description",
                            label: "Scheme that will be used for color generation"
                        })
                    ]
                }),
                ComboBoxText({
                    setup: (self: Gtk.ComboBoxText) => {
                        for (const { key, value } of color_schemes) {
                            self.append_text(key);
                        }
                        let selected: string | null;
                        self.connect("changed", () => {
                            selected = self.get_active_text();
                            theme_settings.scheme.setValue(color_schemes[selected!]);
                            Utils.writeFile(color_schemes[selected!], generation_scheme_file).catch(print);
                            ReloadTheme();
                        });
                    }
                })
            ]
        })
    });

const SwitchRow = (
    on_activate: (...args: any) => void,
    state: boolean | Binding<any, any, boolean>,
    title: string,
    description?: string
) =>
    Widget.EventBox({
        class_name: "row",
        on_primary_click_release: (self) => {
            self.child.children[1]!.activate();
        },
        child: Widget.Box({
            class_name: "row",
            vpack: "start",
            children: [
                // @ts-expect-error
                Widget.Box({
                    vertical: true,
                    hexpand: true,
                    vpack: "center",
                    children: [
                        Widget.Label({
                            hpack: "start",
                            class_name: "title",
                            label: title
                        }),
                        description
                            ? Widget.Label({
                                  hpack: "start",
                                  class_name: "description",
                                  label: description
                              })
                            : undefined
                    ]
                }),
                Widget.Switch({
                    vexpand: false,
                    vpack: "center",
                    hpack: "end",
                    on_activate: on_activate,
                    state: state
                })
            ]
        })
    });

function ToggleConfigVar(name: keyof typeof default_config) {
    config.config = {
        ...config.config,
        [name]: !config.config[name]
    };
}

export function Appearance() {
    const box = Widget.Box({
        vertical: true,
        children: [
            DarkTheme(),
            ThemeColor(),
            ColorScheme(),
            Widget.Separator(),
            SwitchRow(
                () => ToggleConfigVar("always_show_battery"),
                config.config.always_show_battery,
                "Always show battery"
            ),
            SwitchRow(
                () => ToggleConfigVar("show_battery_percent"),
                config.config.show_battery_percent,
                "Show battery percent"
            ),
            SwitchRow(
                () => ToggleConfigVar("show_taskbar"),
                config.config.show_taskbar,
                "Show taskbar",
                "Requires ags restart"
            )
        ]
    });
    return Widget.Scrollable({
        hscroll: "never",
        child: box,
        vexpand: true
    });
}
