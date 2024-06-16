"use strict";
// Import
import Gdk from 'gi://Gdk';
// widgets
import { Bar, BarCornerTopleft, BarCornerTopright } from './modules/bar.js';
import { NotificationPopups } from "./modules/notificationPopups.js"
import { applauncher } from "./modules/applauncher.js"
import { media } from "./modules/media.js"
import { cliphist } from "./modules/cliphist.js"
import { sidebar } from "./modules/sidebar/main.js"
import { wifi } from './modules/wifi.js';
const GLib = imports.gi.GLib;

const range = (length, start = 1) => Array.from({ length }, (_, i) => i + start);
function forMonitors(widget) {
    const n = Gdk.Display.get_default()?.get_n_monitors() || 1;
    return range(n, 0).map(widget).flat(1);
}
function forMonitorsAsync(widget) {
    const n = Gdk.Display.get_default()?.get_n_monitors() || 1;
    return range(n, 0).forEach((n) => widget(n).catch(print))
}

const Windows = () => [
    forMonitors(NotificationPopups),
    forMonitors(BarCornerTopleft),
    forMonitors(BarCornerTopright),
    media,
    applauncher,
    cliphist,
    sidebar,
    wifi
];

const CLOSE_ANIM_TIME = 210;
const closeWindowDelays = {};
for (let i = 0; i < (Gdk.Display.get_default()?.get_n_monitors() || 1); i++) {
    closeWindowDelays[`osk${i}`] = CLOSE_ANIM_TIME;
}

App.config({
    style: `${App.configDir}/style.css`,
    windows: Windows().flat(1),
    stackTraceOnError: true,
    // @ts-ignore
    closeWindowDelay: closeWindowDelays,
    onConfigParsed: function() {
    },
});

function ReloadCSS() {
    App.resetCss()
    App.applyCss(`${App.configDir}/style.css`)
}

function ReloadGtkCSS() {
    App.applyCss(`${GLib.get_home_dir()}/.config/gtk-3.0/gtk.css`)
    ReloadCSS()
}

Utils.monitorFile(
    `${App.configDir}/style.css`,
    ReloadCSS
)

Utils.monitorFile(
    `${GLib.get_home_dir()}/.cache/material/colors.json`,
    ReloadCSS
)

Utils.monitorFile(
    `${GLib.get_home_dir()}/.config/gtk-3.0/gtk.css`,
    ReloadGtkCSS
)
forMonitorsAsync(Bar)
