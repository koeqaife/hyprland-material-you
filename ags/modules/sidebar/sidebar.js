import { Management } from "./management.js"
import { Buttons } from "./buttons.js";
import { Navigation } from "./navigation.js";
const { Gtk } = imports.gi;

export function SideBar() {
    return Widget.Box({
        orientation: Gtk.Orientation.VERTICAL,
        class_name: "sidebar_main_box",
        hexpand: true,
        children: [
            Management(),
            Buttons(),
            Navigation()
            // NotificationsBox()
        ]
    })
}
