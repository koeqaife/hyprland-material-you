import { theme } from "variables.ts";
const GLib = imports.gi.GLib;

let theme_reload_lock = false;
const color_generator = `${GLib.get_home_dir()}/dotfiles/material-colors/generate.py`;

const ReloadTheme = (color: string) => {
    if (theme_reload_lock)
        return
    function Default() {
        Utils.execAsync(`python -O ${color_generator} -w --color-scheme ${theme.value}`)
            .finally(() => { theme_reload_lock = false })
            .then(() => {
                Utils.writeFile("none", `${GLib.get_home_dir()}/dotfiles/.settings/custom-color`)
                .catch(print)
            })
            .catch(print)
    }
    theme_reload_lock = true;
    if (color != "none" && color.length > 6)
        Utils.execAsync(`python -O ${color_generator} --color "${color}" --color-scheme ${theme.value}`)
            .finally(() => { theme_reload_lock = false })
            .then(() => {
                Utils.writeFile(color, `${GLib.get_home_dir()}/dotfiles/.settings/custom-color`)
                .catch(print)
            })
            .catch(err => { print(err); Default() })
    else
        Default()
}

const DarkTheme = () => Widget.EventBox({
    class_name: "row",
    on_primary_click: self => {
        self.child.children[1]!.activate()
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
                    }),
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
                on_activate: self => {
                    if (self.active != (theme.value.trim() == "dark")) {
                        Utils.execAsync(`${App.configDir}/scripts/dark-theme.sh --set ${self.state ? "dark" : "light"}`).catch(print);
                        theme.setValue(self.state ? "dark" : "light");
                    }
                },
                state: theme.bind().as(c => c.trim() == "dark"),
            })
        ]
    })
})

const ThemeColor = () => Widget.EventBox({
    class_name: "row",
    on_primary_click: self => {
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
                    // Widget.Label({
                    //     hpack: "start",
                    //     class_name: "description",
                    //     label: "Idk"
                    // })
                ]
            }),
            Widget.Entry({
                max_length: 7,
                hpack: "end",
                css: "border: 2px solid;",
                on_accept: self => {
                    ReloadTheme(self.text!);
                },
                on_change: self => {
                    if (self.text!.length > 6)
                        self.css = `border: 2px solid; border-color: ${self.text!}`
                }
            })
        ]
    })
})

export function Theme() {
    const box = Widget.Box({
        vertical: true,
        children: [
            DarkTheme(),
            ThemeColor()
        ],
    })
    return Widget.Scrollable({
        hscroll: "never",
        child: box,
        vexpand: true
    })
}