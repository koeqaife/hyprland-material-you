import { NotificationsBox } from "./notifications.ts";
import { SystemBox } from "./system.ts";
let shown = Variable("Messages");
import Gtk from "gi://Gtk?version=3.0";
import { MaterialIcon } from "icons.ts";

type ButtonType = {
    page: string;
    label: string;
    icon: string;
};

function Button({ page, label, icon }: ButtonType) {
    return Widget.Button({
        class_name: "navigation_button",
        hexpand: true,
        attribute: { page: page },
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
                    overlay: MaterialIcon(icon, "20px"),
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
        }
    });
}

export function Navigation() {
    const messages_apps = ["discord", "materialgram", "Telegram Desktop"];
    let stack = Widget.Stack({
        children: {
            Messages: NotificationsBox({ include: messages_apps }),
            Notifications: NotificationsBox({ exclude: messages_apps }),
            System: SystemBox()
        },
        transition: "crossfade",
        transitionDuration: 200,
        // @ts-expect-error
        shown: shown.bind()
    });
    const buttons = Widget.Box({
        class_name: "navigation",
        hexpand: true,
        children: [
            Button({
                page: "Messages",
                label: "Messages",
                icon: "chat"
            }),
            Button({
                page: "Notifications",
                label: "Notifs",
                icon: "notifications"
            }),
            Button({
                page: "System",
                label: "System",
                icon: "info"
            })
        ],
        setup: (self) => {
            self.hook(shown, () => {
                for (const button of self.children) {
                    button.toggleClassName("active", button.attribute.page == shown.value);
                }
            });
        }
    });
    return Widget.Box({
        vexpand: true,
        orientation: Gtk.Orientation.VERTICAL,
        class_name: "sidebar_bottom",
        children: [stack, buttons],
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
