// by koeqaife ;)

import { Variable as VariableType } from "types/variable";
import { MaterialIcon } from "icons";
import config from "services/configuration";
import { type ThemeJson } from "variables";
import { custom_theme } from "variables";

const config_version = "2";
const themes_folder = `${App.configDir}/themes`;
const get_themes_cmd = `python -OOO ${App.configDir}/scripts/themes.py -a ${themes_folder}`;
let _themes = Utils.exec(get_themes_cmd);
const themes: VariableType<ThemeJson[]> = Variable(JSON.parse(_themes));
const focused: VariableType<ThemeJson | null> = Variable<ThemeJson | null>(null);

const DEFAULT: ThemeJson = {
    name: "Default",
    author: "koeqaife",
    config_version: "universal",
    description: "Hyprland-material-you theme",
    hide: false,
    load_default_css: true,
    path: undefined,
    version: "unknown"
};
const MESSAGES = {
    may_not_be_compatible: "This theme may not be compatible with the current version of hyprland-material-you.",
    unknown_version: "This theme does not specify ConfigVersion, the theme may not be compatible."
};

const theme = (theme: ThemeJson) =>
    Widget.Button({
        class_name: "row theme",
        hexpand: true,
        vpack: "start",
        setup: (self) => {
            if (config.config.current_theme == theme.path) focused.setValue(theme);
            self.hook(focused, () => {
                self.toggleClassName("focused", focused.value == theme);
            });
        },
        on_clicked: () => {
            focused.setValue(theme);
        },
        child: Widget.Box({
            vertical: true,
            hexpand: true,
            vpack: "center",
            children: [
                Widget.Label({
                    hpack: "start",
                    class_name: "title",
                    label: theme.name,
                    truncate: "end"
                }),
                // @ts-expect-error
                Widget.Box({
                    children: [
                        theme.config_version == "universal" ||
                        (theme.config_version != "0" && theme.config_version == config_version)
                            ? null
                            : MaterialIcon("error", "18px", {
                                  tooltip_text:
                                      theme.config_version == "0"
                                          ? MESSAGES.unknown_version
                                          : MESSAGES.may_not_be_compatible
                              }),
                        Widget.Label({
                            hpack: "start",
                            class_name: "description",
                            label: `${theme.description} (by ${theme.author})`,
                            truncate: "end"
                        })
                    ]
                })
            ]
        })
    });

const theme_list = () => {
    const reload = () => {
        Utils.execAsync(get_themes_cmd).then((out) => {
            themes.setValue(JSON.parse(out));
        });
    };
    const _default = theme(DEFAULT);
    const box = Widget.Box({
        vertical: true,
        children: [_default, ...themes.value.filter((value) => !value.hide).map((value) => theme(value))],
        vexpand: true,
        attribute: {
            reload: reload
        },
        setup: (self) => {
            self.hook(themes, () => {
                try {
                    box.children = [
                        _default,
                        ...themes.value.filter((value) => !value.hide).map((value) => theme(value))
                    ];
                } catch (e) {
                    print("Error while reloading themes:", e);
                }
            });
        }
    });
    return box;
};

export const Themes = () => {
    const _box = theme_list();
    const _actions = Widget.Box({
        class_name: "actions",
        hpack: "end",
        spacing: 5,
        children: [
            Widget.Button({
                hpack: "end",
                class_name: "standard_button",
                label: "Reload",
                on_clicked: () => {
                    _box.attribute.reload();
                }
            }),
            Widget.Button({
                hpack: "end",
                class_name: "filled_button",
                label: "Select",
                on_clicked: () => {
                    custom_theme.setValue(null);
                    config.config = {
                        ...config.config,
                        current_theme: focused.value?.path || null
                    };
                }
            })
        ]
    });
    const _bottom = Widget.Box({
        hexpand: true,
        vertical: true,
        class_name: "bottom_bar",
        children: [_actions]
    });
    return Widget.Box({
        vertical: true,
        class_name: "themes",
        children: [_box, _bottom]
    });
};
