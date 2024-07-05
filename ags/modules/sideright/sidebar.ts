import { Management } from "./management.ts";
import { Buttons } from "./buttons.ts";
import { Navigation } from "./navigation.ts";
import Gtk from "gi://Gtk?version=3.0";

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
    });
}
