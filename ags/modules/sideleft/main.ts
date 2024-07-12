import popupwindow from "../misc/popupwindow.ts";
import Gtk from "gi://Gtk?version=3.0";
import { MaterialIcon } from "icons.ts";
import { WeatherBox } from "./weather.ts";
import { Media } from "./players.ts";
import { Applauncher } from "./applauncher.ts";
import { geminiPage } from "./gemini.ts";
import { chatsPage } from "./chats.ts";

export const WINDOW_NAME = "sideleft";
export const shown = Variable("weather");

export function toggleAppsWindow() {
    if (shown.value == "apps" && sideleft.visible) App.closeWindow(WINDOW_NAME);
    else {
        App.openWindow(WINDOW_NAME);
        shown.setValue("apps");
    }
}
export function toggleMediaWindow() {
    if (shown.value == "media" && sideleft.visible) App.closeWindow(WINDOW_NAME);
    else {
        App.openWindow(WINDOW_NAME);
        shown.setValue("media");
    }
}

globalThis.toggleMediaWindow = toggleMediaWindow;
globalThis.toggleAppsWindow = toggleAppsWindow;

type ButtonType = {
    page: string;
    label: string;
    icon?: string;
    icon_widget?: Gtk.Widget;
};

function Button({ page, label, icon, icon_widget }: ButtonType) {
    return Widget.Button({
        class_name: `navigation_button _${page}`,
        hexpand: true,
        vpack: "start",
        child: Widget.Box({
            orientation: Gtk.Orientation.VERTICAL,
            class_name: "container_outer",
            children: [
                Widget.Overlay({
                    child: Widget.Box({
                        orientation: Gtk.Orientation.VERTICAL,
                        hpack: "center",
                        class_name: "container"
                    }),
                    overlay: icon ? MaterialIcon(icon!, "20px") : icon_widget!,
                    pass_through: true
                }),
                Widget.Label({
                    label: label,
                    class_name: "label"
                })
            ]
        }),
        on_clicked: () => {
            shown.setValue(page);
        },
        setup: (self) => {
            self.hook(shown, () => {
                self.toggleClassName("active", shown.value == page);
            });
        }
    });
}

function Navigation() {
    let stack = Widget.Stack({
        children: {
            weather: WeatherBox(),
            media: Media(),
            apps: Applauncher(),
            gemini: geminiPage,
            chats: chatsPage
        },
        hexpand: true,
        transition: "crossfade",
        transitionDuration: 200,
        // @ts-expect-error
        shown: shown.bind()
    });
    const buttons = Widget.Box({
        class_name: "rail",
        vertical: true,
        vexpand: true,
        hpack: "start",
        children: [
            Button({
                page: "weather",
                label: "Weather",
                icon: "cloud"
            }),
            Button({
                page: "media",
                label: "Players",
                icon: "music_note"
            }),
            Button({
                page: "apps",
                label: "Apps",
                icon: "search"
            }),
            Button({
                page: "gemini",
                label: "Gemini",
                icon_widget: Widget.Icon({
                    icon: "google-gemini-symbolic",
                    size: 20,
                    class_name: "icon"
                })
            }),
            Button({
                page: "chats",
                label: "Chat",
                icon: "chat"
            })
        ]
    });
    return Widget.Box({
        vexpand: true,
        class_name: "sideleft",
        children: [buttons, stack],
        hexpand: true,
        setup: (self) => {
            const keys = Object.keys(stack.children);
            for (let i = 0; i < keys.length; i++) {
                const key = keys[i];
                // @ts-expect-error
                self.keybind(`${i + 1}`, () => {
                    shown.setValue(key);
                });
            }
        }
    });
}

function SideLeft() {
    return Widget.Box({
        class_name: "sideleft_main_box",
        hexpand: true,
        children: [Navigation()]
    });
}

export const sideleft = popupwindow({
    name: WINDOW_NAME,

    class_name: "sideleft",
    visible: false,
    keymode: "exclusive",
    child: SideLeft(),
    anchor: ["top", "left", "bottom"],
    css: "min-width: 443px;"
});
