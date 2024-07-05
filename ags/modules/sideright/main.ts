import popupwindow from "../misc/popupwindow.js";
import { SideBar } from "./sidebar.ts";

export const WINDOW_NAME = "sidebar";

export const sideright = popupwindow({
    name: WINDOW_NAME,

    class_name: "sidebar",
    visible: false,
    keymode: "exclusive",
    child: SideBar(),
    anchor: ["top", "right", "bottom"],
    css: "min-width: 443px;"
});
