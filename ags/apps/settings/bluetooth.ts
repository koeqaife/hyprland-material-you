import { PageTitle } from "./main";
import Gtk from "gi://Gtk?version=3.0"

const bluetooth = await Service.import("bluetooth")

export const Bluetooth = () => Widget.Box({
    hexpand: true,
    vexpand: true,
    child: Widget.Label({
        label: "Not implemented yet",
    })
}) 