const { Gtk } = imports.gi;
import { NotificationsBox } from "./notifications.ts"
import { SystemBox } from "./system.ts"
let shown = Variable("Messages");


function Button({ page, label, icon }) {
    return Widget.Box({
        hexpand: true,
        child: Widget.Button({
            class_name: shown.bind().as(_page => _page == page ? "navigation_button active" : "navigation_button"),
            child: Widget.Box({
                orientation: Gtk.Orientation.VERTICAL,
                class_name: "container_outer",
                children: [
                    Widget.Box({
                        orientation: Gtk.Orientation.VERTICAL,
                        halign: Gtk.Align.CENTER,
                        class_name: "container",
                        child: Widget.Label({
                            hexpand: true,
                            label: icon,
                            class_name: "awesome_icon icon"
                        }),
                    }),
                    Widget.Label({
                        label: label,
                        class_name: "label",
                        hexpand: true,
                    })
                ]
            }),
            on_clicked: () => {
                shown.setValue(page)
            }
        })
    })
}


export function Navigation() {
    const messages_apps = ["discord", "materialgram", "Telegram Desktop"]
    let stack = Widget.Stack({
        children: {
            "Messages": NotificationsBox({ include: messages_apps }),
            "Notifications": NotificationsBox({ exclude: messages_apps }),
            "System": SystemBox()
        },
        transition: "crossfade",
        transitionDuration: 200,
        // @ts-ignore
        shown: shown.bind()
    })
    const buttons = Widget.Box({
        class_name: "navigation",
        hexpand: true,
        children: [
            Button({
                page: "Messages",
                label: "Messages",
                icon: ""
            }),
            Button({
                page: "Notifications",
                label: "Notifs",
                icon: ""
            }),
            Button({
                page: "System",
                label: "System",
                icon: ""
            })
        ]
    })
    return Widget.Box({
        vexpand: true,
        orientation: Gtk.Orientation.VERTICAL,
        class_name: "sidebar_bottom",
        children: [
            stack,
            buttons
        ]
    })
}
