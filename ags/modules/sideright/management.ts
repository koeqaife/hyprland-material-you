const notifications = await Service.import("notifications");
const network = await Service.import("network");
const bluetooth = await Service.import("bluetooth");
import { OpenSettings } from "apps/settings/main.ts";
import { WINDOW_NAME } from "./main.ts";
import { idle_inhibitor, night_light, theme } from "variables.ts";
import { MaterialIcon } from "icons.ts";

import Gtk from "gi://Gtk?version=3.0";

const current_page = Variable(0);

function WifiIndicator() {
    const ssid = Widget.Label({
        label: "Unknown",
        visible: false,
        class_name: "ssid",
        xalign: 0,
        vpack: "center",
        truncate: "end"
    });
    const name = Widget.Box({
        vertical: true,
        vpack: "center",
        children: [
            Widget.Box([
                Widget.Label({
                    label: "Internet",
                    vpack: "center"
                })
            ]),
            ssid
        ]
    });
    return Widget.Box({
        css: "padding-left: 15px; padding-right: 15px; padding-top: 5px; padding-bottom: 5px;",
        children: [
            MaterialIcon("signal_wifi_4_bar", "20px"),
            name,
            Widget.Box({
                hpack: "end",
                hexpand: true,
                child: MaterialIcon("chevron_right", "20px", {
                    class_name: "material_icon icon arrow"
                })
            })
        ],
        setup: (self) => {
            self.hook(network, () => {
                ssid.label = network.wifi.ssid || "Unknown";
                ssid.visible = !!network.wifi.ssid;
            });
        }
    });
}

const WiredIndicator = () =>
    Widget.Box({
        css: "padding-left: 15px; padding-right: 15px; padding-top: 5px; padding-bottom: 5px;",
        children: [
            MaterialIcon("settings_ethernet", "20px"),
            Widget.Label({
                label: "Internet"
            })
        ]
    });

const NetworkIndicator = () =>
    Widget.Stack({
        children: {
            wifi: WifiIndicator(),
            wired: WiredIndicator()
        },
        shown: network.bind("primary").as((p) => p || "wifi")
    });

function IconAndName({ label, icon, arrow = false }) {
    let box = Widget.Box({
        css: "padding-left: 15px; padding-right: 15px; padding-top: 5px; padding-bottom: 5px;",
        children: [
            MaterialIcon(icon, "20px"),
            Widget.Label({
                label: label,
                justification: "center"
            })
        ]
    });
    if (arrow) {
        const arrow = Widget.Box({
            hpack: "end",
            hexpand: true,
            child: MaterialIcon("chevron_right", "20px", {
                class_name: "material_icon icon arrow"
            })
        });
        // @ts-ignore
        box.children = [...box.children, arrow];
    }
    return box;
}

function Page1() {
    return Widget.Box({
        orientation: Gtk.Orientation.VERTICAL,
        spacing: 5,
        hexpand: true,
        class_name: "management_box",
        children: [
            Widget.Box({
                orientation: Gtk.Orientation.HORIZONTAL,
                hexpand: true,
                spacing: 5,
                children: [
                    Widget.Button({
                        hexpand: true,
                        class_name: "management_button",
                        child: NetworkIndicator(),
                        on_primary_click_release: () => {
                            network.toggleWifi();
                        },
                        on_secondary_click_release: () => {
                            App.closeWindow(WINDOW_NAME);
                            OpenSettings("network");
                        },
                        setup: (self) => {
                            if (network.wifi)
                                self.hook(network.wifi, () => {
                                    self.toggleClassName("active", network.wifi.enabled);
                                });
                        }
                    }),
                    Widget.Button({
                        hexpand: true,
                        class_name: "management_button",
                        child: IconAndName({
                            label: "Bluetooth",
                            icon: "bluetooth",
                            arrow: true
                        }),
                        on_primary_click_release: () => {
                            bluetooth.toggle();
                        },
                        on_secondary_click_release: () => {
                            OpenSettings("bluetooth");
                            App.closeWindow(WINDOW_NAME);
                        },
                        setup: (self) => {
                            self.hook(bluetooth, () => {
                                self.toggleClassName("active", bluetooth.enabled);
                            });
                        }
                    })
                ]
            }),
            Widget.Box({
                orientation: Gtk.Orientation.HORIZONTAL,
                spacing: 5,
                hexpand: true,
                children: [
                    Widget.Button({
                        hexpand: true,
                        class_name: "management_button",
                        on_clicked: () => {
                            Utils.execAsync(`${App.configDir}/scripts/dark-theme.sh --toggle`).catch(print);
                            theme.setValue(theme.value.trim() == "dark" ? "light" : "dark");
                        },
                        child: IconAndName({
                            label: "Dark theme",
                            icon: "contrast"
                        }),
                        setup: (self) => {
                            self.hook(theme, () => {
                                self.toggleClassName("active", theme.value.trim() == "dark");
                            });
                        }
                    }),
                    Widget.Button({
                        hexpand: true,
                        class_name: "management_button",
                        on_clicked: () => {
                            notifications.dnd = !notifications.dnd;
                        },
                        child: IconAndName({
                            label: "Do Not Disturb",
                            icon: "do_not_disturb_off"
                        }),
                        setup: (self) => {
                            notifications.connect("notify::dnd", (_) => {
                                self.toggleClassName("active", notifications.dnd);
                                self.child.children[0].label = notifications.dnd
                                    ? "do_not_disturb_on"
                                    : "do_not_disturb_off";
                            });
                        }
                    })
                ]
            }),
            Widget.Box({
                orientation: Gtk.Orientation.HORIZONTAL,
                spacing: 5,
                hexpand: true,
                children: [
                    Widget.Button({
                        hexpand: true,
                        class_name: "management_button",
                        child: IconAndName({
                            label: "Idle inhibitor",
                            icon: "schedule"
                        }),
                        on_clicked: () => {
                            idle_inhibitor.setValue(!idle_inhibitor.value);
                            if (idle_inhibitor.value)
                                Utils.execAsync([
                                    "bash",
                                    "-c",
                                    `pidof wayland-idle-inhibitor.py || ${App.configDir}/scripts/wayland-idle-inhibitor.py`
                                ]).catch(print);
                            else Utils.execAsync("pkill -f wayland-idle-inhibitor.py").catch(print);
                        },
                        setup: (self) => {
                            idle_inhibitor.setValue(!!Utils.exec("pidof wayland-idle-inhibitor.py"));
                            self.hook(idle_inhibitor, () => {
                                self.toggleClassName("active", idle_inhibitor.value);
                            });
                        }
                    }),
                    Widget.Button({
                        hexpand: true,
                        class_name: "management_button",
                        child: IconAndName({
                            label: "Night Light",
                            icon: "nightlight"
                        }),
                        on_clicked: () => {
                            night_light.setValue(!night_light.value);
                            Utils.execAsync(`${App.configDir}/scripts/night-light.sh --toggle`)
                                .then((out) => {
                                    night_light.setValue(out.trim() == "enabled");
                                })
                                .catch((err) => {
                                    night_light.setValue(!night_light.value);
                                });
                        },
                        setup: (self) => {
                            self.hook(night_light, () => {
                                self.toggleClassName("active", night_light.value);
                            });
                        }
                    })
                ]
            })
        ]
    });
}

function Page2() {
    return Widget.Box({
        orientation: Gtk.Orientation.VERTICAL,
        spacing: 5,
        hexpand: true,
        class_name: "management_box",
        children: [
            Widget.Box({
                orientation: Gtk.Orientation.HORIZONTAL,
                spacing: 5,
                children: [
                    Widget.Button({
                        hexpand: true,
                        class_name: "management_button",
                        child: IconAndName({
                            label: "Color picker",
                            icon: "colorize",
                            arrow: true
                        }),
                        on_clicked: () => {
                            App.closeWindow(WINDOW_NAME);
                            Utils.execAsync("sleep 0.5")
                                .then(() => Utils.execAsync("hyprpicker -a").catch(print))
                                .catch(print);
                        }
                    }),
                    Widget.Button({
                        hexpand: true,
                        class_name: "management_button",
                        child: IconAndName({
                            label: "Settings",
                            icon: "settings",
                            arrow: true
                        }),
                        on_clicked: () => {
                            OpenSettings();
                            App.closeWindow(WINDOW_NAME);
                        }
                    })
                ]
            })
        ]
    });
}

const DotButton = (index: number) =>
    Widget.Button({
        label: "●",
        on_clicked: () => current_page.setValue(index),
        class_name: "dotbutton",
        hexpand: false,
        setup: (self) => {
            self.hook(current_page, () => {
                self.toggleClassName("active", current_page.value == index);
            });
        }
    });

export function Management() {
    let pages = {
        page1: Page1(),
        page2: Page2()
    };
    const number_of_pages = Object.keys(pages).length;
    const page_names = Array.from({ length: number_of_pages }, (_, i) => `page${i + 1}`);

    const stack = Widget.Stack({
        children: pages,
        // @ts-expect-error
        shown: current_page.bind().as((v) => `page${v + 1}`),
        transition: "slide_left_right",
        transition_duration: 200
    });
    const dot_buttons = page_names.map((_, index) => DotButton(index));
    return Widget.EventBox({
        on_scroll_up: () => current_page.setValue(Math.min(current_page.value + 1, number_of_pages - 1)),
        on_scroll_down: () => current_page.setValue(Math.max(current_page.value - 1, 0)),
        child: Widget.Box({
            orientation: Gtk.Orientation.VERTICAL,
            children: [
                stack,
                Widget.Box({
                    children: dot_buttons,
                    class_name: "dotbuttons_box",
                    hpack: "center"
                })
            ],
            setup: (self) => {
                for (let page in page_names) {
                    // @ts-expect-error
                    self.keybind(`${Number(page.replace("page", "")) + 1}`, () => {
                        current_page.setValue(Number(page.replace("page", "")));
                    });
                }
            }
        })
    });
}
