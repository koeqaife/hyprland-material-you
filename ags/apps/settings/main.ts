import { RegularWindow } from "apps/window";
import { Network } from "./network";
import { Bluetooth } from "./bluetooth";
import { Theme } from "./theme";
import { Wallpapers } from "./wallpapers";
import { Info } from "./info";
import { Apps } from "./apps";
import { MaterialIcon } from "icons";
const hyprland = await Service.import("hyprland")
import Gtk from "gi://Gtk?version=3.0"

globalThis.OpenSettings = OpenSettings;
let current_window;
const current_tab = Variable("network");

export async function OpenSettings(cur_tab: string = "network") {
    if (current_window) {
        const _current_workspace = hyprland.active.workspace.id;
        const _client = hyprland.clients.find(client => {
            return (client.class == "com.github.Aylur.ags" && client.title == "Settings")
        })
        if (_client && _current_workspace != _client.workspace.id) {
            current_tab.setValue(cur_tab)
            print("a")
            current_window.hide()
            current_window.show()
            // current_window.destroy();
            // current_window = undefined;
            // SettingsWindow(cur_tab);
        }
        else
            current_tab.setValue(cur_tab)
    }
    else
        SettingsWindow(cur_tab);
}


function Settings(cur_tab: string) {
    current_tab.setValue(cur_tab);
    const stack = Widget.Stack({
        // @ts-ignore
        shown: current_tab.bind(),
        vexpand: true,
        hexpand: true,
        transition: "crossfade",
        children: {
            "network": Page(Network(), "Network"),
            "bluetooth": Page(Bluetooth(), "Bluetooth"),
            "theme": Page(Theme(), "Theme"),
            "wallpaper": Page(Wallpapers(), "Wallpapers"),
            "info": Page(Info(), "Info"),
            "apps": Page(Apps(), "Apps")
        }
    })
    const Row = (name: string, label: string, icon: string = "image-missing") => Widget.Button({
        on_clicked: () => { current_tab.setValue(name) },
        child: Widget.Box({
            children: [
                MaterialIcon(icon),
                Widget.Label(label)
            ]
        }),
        class_name: current_tab.bind().as(c => c == name ? "row active" : "row")
    })
    const sidebar = Widget.Box({
        vertical: true,
        vexpand: true,
        class_name: "sidebar",
        spacing: 2,
        children: [
            Row("network", "Network", "signal_wifi_4_bar"),
            Row("bluetooth", "Bluetooth", "bluetooth"),
            Widget.Separator(),
            Row("theme", "Theme", "palette"),
            Row("wallpaper", "Wallpapers", "image"),
            Widget.Separator(),
            Row("apps", "Apps", "grid_view"),
            Widget.Separator(),
            Row("info", "Info", "info")
        ]
    })
    return Widget.Box({
        hexpand: true,
        vexpand: true,
        vertical: false,
        css: "background-color: @surface",
        children: [
            Widget.Box({
                class_name: "full_sidebar",
                vertical: true,
                children: [
                    Widget.Label({
                        class_name: "settings_title",
                        label: "Settings"
                    }),
                    Widget.Scrollable({
                        hscroll: "never",
                        child: sidebar
                    }),
                ]
            }),
            stack
        ]
    });
}


export const Page = (widget: Gtk.Widget, name: string) => Widget.Box({
    vertical: true,
    children: [
        PageTitle(name),
        widget
    ]
})


export const PageTitle = (label: string) => Widget.Box({
    class_name: "page_title",
    child: Widget.Label({
        label: label,
        hpack: "start"
    })
})


export const SettingsWindow = (cur_tab: string) => {
    let window = RegularWindow({
        title: "Settings",
        default_height: 600,
        default_width: 850,
        class_name: "settings",
        child: Settings(cur_tab),
        setup(win) {
            current_window = win;
        },
        visible: true,
    });
    // @ts-ignore
    window.on("delete-event", () => {
        // @ts-ignore
        window.destroy()
        current_window = undefined;
        return true
    })
    return window
}