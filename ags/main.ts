"use strict";
// Import
import Gdk from "gi://Gdk";
// widgets
import { Bar, BarCornerTopLeft, BarCornerTopRight } from "./modules/bar.ts";
import { Notifications } from "./modules/notificationPopups.ts";
import { cliphist } from "./modules/cliphist.ts";
import { sideright } from "./modules/sideright/main.ts";
import { sideleft } from "./modules/sideleft/main.ts";
import {} from "apps/settings/main.ts";
import {} from "apps/emoji/main.ts";
import { cheatsheet } from "modules/cheatsheet.ts";
import Window from "types/widgets/window";
import { popups } from "modules/popups.ts";
import { start_battery_warning_service } from "services/battery_warning.ts";
import { audio_popup } from "./modules/audio.ts"
import { calendar } from "modules/calendar.ts";
import Gtk from "gi://Gtk?version=3.0";
const GLib = imports.gi.GLib;

const range = (length: number, start = 1) => Array.from({ length }, (_, i) => i + start);
function forMonitors(widget: (index: number) => Window<any, any>): Window<any, any>[] {
    const n = Gdk.Display.get_default()?.get_n_monitors() || 1;
    return range(n, 0).map(widget).flat(1);
}
function forMonitorsAsync(widget: (index: number) => Promise<Window<any, any>>) {
    const n = Gdk.Display.get_default()?.get_n_monitors() || 1;
    return range(n, 0).forEach((n) => widget(n).catch(print));
}

const Windows = () => [
    forMonitors(Notifications),
    forMonitors(BarCornerTopLeft),
    forMonitors(BarCornerTopRight),
    cliphist,
    sideright,
    cheatsheet,
    sideleft,
    forMonitors(popups),
    audio_popup,
    calendar
];

App.config({
    windows: Windows().flat(1),
    // @ts-ignore
    onConfigParsed: function () {}
});

function reload_css() {
    App.resetCss();
    App.applyCss(`${GLib.get_home_dir()}/.config/gtk-3.0/gtk.css`);
    App.applyCss(`${App.configDir}/style.css`);
    App.applyCss(`${App.configDir}/style-apps.css`);
}

function reload_colors() {
    App.applyCss(`${GLib.get_home_dir()}/.cache/material/colors.css`);
}

Utils.monitorFile(`${GLib.get_home_dir()}/.cache/material/colors.css`, reload_css);

forMonitorsAsync(Bar);
reload_css();

function enable_animations(bool: boolean) {
    const settings = Gtk.Settings.get_default()!;

    settings.gtk_enable_animations = bool;
}

globalThis.ReloadCSS = reload_css;
globalThis.ReloadColors = reload_colors;
globalThis.enableAnimations = enable_animations;

globalThis.reload_css = reload_css;
globalThis.reload_colors = reload_colors;
globalThis.enable_animations = enable_animations;

start_battery_warning_service();
