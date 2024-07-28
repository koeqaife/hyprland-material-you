"use strict";
// Import
import Gdk from "gi://Gdk";
const Battery = await Service.import("battery");
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
const GLib = imports.gi.GLib;


const criticalPowerNotification = {
  title: "Battery exhausted",
  body: "Shutdown imminent"
};

const lowPowerNotification = {
  title: "Battery low",
  body: "Plug the cable!"
};

const chargedPowerNotification = {
  title: "Battery full",
  body: "You can unplug the cable"
};

let lastNotification = "";

Battery.connect("notify::percent", () => {
  if (Battery.charged === true) {
    if (lastNotification !== "charged") {
      Utils.notify(chargedPowerNotification.title, chargedPowerNotification.body);
      lastNotification = "charged";
    }
  } else if (Battery.percent === 66 && Battery.charging === false) {
    if (lastNotification !== "low") {
      Utils.notify(lowPowerNotification.title, lowPowerNotification.body);
      lastNotification = "low";
    }
  } else if (Battery.percent === 65 && Battery.charging === false) {
    if (lastNotification !== "critical") {
      Utils.notify(criticalPowerNotification.title, criticalPowerNotification.body);
      lastNotification = "critical";
    }
  } else {
    lastNotification = "";
  }
});



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
    forMonitors(popups)
];

const CLOSE_ANIM_TIME = 210;
const closeWindowDelays = {};
for (let i = 0; i < (Gdk.Display.get_default()?.get_n_monitors() || 1); i++) {
    closeWindowDelays[`osk${i}`] = CLOSE_ANIM_TIME;
}

App.config({
    windows: Windows().flat(1),
    // @ts-ignore
    closeWindowDelay: closeWindowDelays,
    onConfigParsed: function () {}
});

function ReloadCSS() {
    App.resetCss();
    App.applyCss(`${App.configDir}/style.css`);
    App.applyCss(`${App.configDir}/style-apps.css`);
}

function ReloadGtkCSS() {
    App.applyCss(`${GLib.get_home_dir()}/.config/gtk-3.0/gtk.css`);
    ReloadCSS();
}

Utils.monitorFile(`${App.configDir}/style.css`, ReloadCSS);

Utils.monitorFile(`${App.configDir}/style-apps.css`, ReloadCSS);

Utils.monitorFile(`${GLib.get_home_dir()}/.cache/material/colors.json`, ReloadCSS);

Utils.monitorFile(`${GLib.get_home_dir()}/.config/gtk-3.0/gtk.css`, ReloadGtkCSS);
forMonitorsAsync(Bar);
ReloadGtkCSS();

start_battery_warning_service()
