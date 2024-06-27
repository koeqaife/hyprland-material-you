
const notifications = await Service.import("notifications")
const network = await Service.import('network')
import { OpenSettings } from "apps/settings/main.ts";
import { WINDOW_NAME } from "./main.ts"
import { bluetooth_enabled, idle_inhibitor, night_light, theme } from "variables.ts";

const { Gtk } = imports.gi;

const currentPage = Variable(0);

function WifiIndicator() {
    return Widget.Box({
        css: "padding-left: 15px; padding-right: 15px; padding-top: 5px; padding-bottom: 5px;",
        children: [
            Widget.Label({
                label: "\udb82\udd28",
                class_name: "awesome_icon",
                css: `font-weight: bold; font-size: 20px; margin-right: 0.60em;`,
            }),
            Widget.Box({
                visible: network.wifi.bind('enabled'),
                orientation: Gtk.Orientation.VERTICAL,
                children: [
                    Widget.Box([
                        Widget.Label({
                            label: "Internet",
                        }),
                    ]),
                    Widget.Label({
                        label: network.wifi.bind('ssid')
                            .as(ssid => ssid || 'Unknown'),
                        class_name: "ssid",
                        xalign: 0,
                        vpack: "center",
                        truncate: "end",
                    }),
                ]
            }),
            Widget.Label({
                visible: network.wifi.bind('enabled').as(enabled => !enabled),
                label: "Internet",
            }),
            Widget.Box({
                halign: Gtk.Align.END,
                hexpand: true,
                child: Widget.Label({
                    label: "",
                    class_name: "awesome_icon",
                    css: `font-weight: normal; font-size: 15px;`,
                })
            })
        ],
    })
}

const WiredIndicator = () => Widget.Box({
    css: "padding-left: 15px; padding-right: 15px; padding-top: 5px; padding-bottom: 5px;",
    children: [
        Widget.Icon({
            icon: network.wired.bind('icon_name'),
        }),
        Widget.Label({
            label: "Internet",
        }),
    ]
})


const NetworkIndicator = () => Widget.Stack({
    children: {
        wifi: WifiIndicator(),
        wired: WiredIndicator(),
    },
    shown: network.bind('primary').as(p => p || 'wifi'),
})


function IconAndName({ label, icon, padding = "0.3em", arrow = false }) {
    let box = Widget.Box({
        css: "padding-left: 15px; padding-right: 15px; padding-top: 5px; padding-bottom: 5px;",
        children: [
            Widget.Label({
                label: icon,
                class_name: "awesome_icon",
                css: `font-weight: bold; font-size: 20px; margin-right: ${padding};`,
            }),
            Widget.Label({
                label: label,
                justification: "center",
            }),
        ]
    })
    if (arrow) {
        const arrow = Widget.Box({
            halign: Gtk.Align.END,
            hexpand: true,
            child: Widget.Label({
                label: "",
                class_name: "awesome_icon",
                css: `font-weight: normal; font-size: 15px;`,
            })
        })
        // @ts-ignore
        box.children = [...box.children, arrow]
    }
    return box
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
                spacing: 2.5,
                children: [
                    Widget.Button({
                        hexpand: true,
                        class_name: network.wifi.bind("enabled")
                            .as(enabled => enabled ? "management_button active" : "management_button"),
                        child: NetworkIndicator(),
                        on_primary_click: () => {
                            network.toggleWifi();
                        },
                        on_secondary_click: () => {
                            App.closeWindow(WINDOW_NAME)
                            OpenSettings("network")
                        }
                    }),
                    Widget.Button({
                        hexpand: true,
                        class_name: bluetooth_enabled.bind()
                            .as(state => state.trim() == "yes" ? "management_button active" : "management_button"
                            ),
                        child: IconAndName({
                            label: "Bluetooth",
                            icon: "󰂯",
                            arrow: true,
                        }),
                        on_primary_click: () => {
                            Utils.execAsync(`${App.configDir}/scripts/bluetooth.sh --toggle`)
                                .then(out => { bluetooth_enabled.setValue(out) })
                        },
                        on_secondary_click: () => {
                            Utils.execAsync("blueman-manager")
                            App.closeWindow(WINDOW_NAME)
                        }
                    })
                ]
            }),
            Widget.Box({
                orientation: Gtk.Orientation.HORIZONTAL,
                spacing: 2.5,
                hexpand: true,
                children: [
                    Widget.Button({
                        hexpand: true,
                        class_name: theme.bind().as((str) => {
                            return str.trim() == "dark" ? "management_button active" : "management_button"
                        }),
                        on_clicked: () => {
                            Utils.execAsync(`${App.configDir}/scripts/dark-theme.sh --toggle`).catch(print);
                            theme.setValue(theme.value.trim() == "dark" ? "light" : "dark");
                        },
                        child: IconAndName({
                            label: "Dark theme",
                            icon: ""
                        })
                    }),
                    Widget.Button({
                        hexpand: true,
                        class_name: notifications.bind("dnd").as((bool) => {
                            return bool ? "management_button active" : "management_button";
                        }),
                        on_clicked: () => {
                            notifications.dnd = notifications.dnd ? false : true
                        },
                        child: IconAndName({
                            label: "Do Not Disturb",
                            icon: ""
                        })
                    })
                ]
            }),
            Widget.Box({
                orientation: Gtk.Orientation.HORIZONTAL,
                spacing: 2.5,
                hexpand: true,
                children: [
                    Widget.Button({
                        hexpand: true,
                        class_name: idle_inhibitor.bind()
                            .as(bool => bool ? "management_button active" : "management_button"),
                        child: IconAndName({
                            label: "Idle inhibitor",
                            icon: ""
                        }),
                        onClicked: () => {
                            idle_inhibitor.setValue(!idle_inhibitor.value)
                            if (idle_inhibitor.value) Utils.execAsync(['bash', '-c', `pidof wayland-idle-inhibitor.py || ${App.configDir}/scripts/wayland-idle-inhibitor.py`]).catch(print)
                            else Utils.execAsync('pkill -f wayland-idle-inhibitor.py').catch(print);
                        },
                        setup: () => {
                            idle_inhibitor.setValue(!!Utils.exec('pidof wayland-idle-inhibitor.py'));
                        },
                    }),
                    Widget.Button({
                        hexpand: true,
                        class_name: night_light.bind()
                            .as(mode => mode ? "management_button active" : "management_button"),
                        child: IconAndName({
                            label: "Night Light",
                            icon: ""
                        }),
                        onClicked: () => {
                            night_light.setValue(!night_light.value)
                            Utils.execAsync(`${App.configDir}/scripts/night-light.sh --toggle`)
                                .then(out => {
                                    if (out.trim() == "enabled") night_light.setValue(true)
                                    else if (out.trim() == "disabled") night_light.setValue(false)
                                })
                                .catch(err => {
                                    night_light.setValue(!night_light.value);
                                });
                        },
                        setup: () => {
                            Utils.execAsync(`${App.configDir}/scripts/night-light.sh --get`)
                                .then(out => {
                                    if (out.trim() == "enabled") night_light.setValue(true)
                                    else if (out.trim() == "disabled") night_light.setValue(false)
                                })
                                .catch(print);
                        }
                    })
                ]
            })
        ]
    })
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
                spacing: 2.5,
                children: [
                    Widget.Button({
                        hexpand: true,
                        class_name: "management_button",
                        child: IconAndName({
                            label: "Color picker",
                            icon: "",
                            arrow: true,
                        }),
                        on_primary_click: () => {
                            App.closeWindow(WINDOW_NAME);
                            Utils.execAsync("sleep 0.5")
                                .then(() =>
                                    Utils.execAsync("hyprpicker -a").catch(print)
                                )
                                .catch(print);
                        }
                    }),
                    Widget.Button({
                        hexpand: true,
                        class_name: "management_button disabled",
                    }),
                ]
            })
        ]
    })
}

const createDotButton = (index: number) => Widget.Button({
    label: '●',
    onClicked: () => currentPage.setValue(index),
    class_name: currentPage.bind().as(v => v == index ? "dotbutton active" : "dotbutton"),
    hexpand: false,
});


export function Management() {
    let pages = {
        "page1": Page1(),
        "page2": Page2()
    }
    const numberOfPages = Object.keys(pages).length;
    const pageNames = Array.from({ length: numberOfPages }, (_, i) => `page${i + 1}`);

    const stack = Widget.Stack({
        children: pages,
        // @ts-ignore
        shown: currentPage.bind().as(v => `page${v + 1}`),
        transition: "slide_left_right",
        transitionDuration: 200,
    })
    const dotButtons = pageNames.map((_, index) => createDotButton(index));
    return Widget.EventBox({
        onScrollUp: () => currentPage.setValue((currentPage.value + 1) % numberOfPages),
        onScrollDown: () => {
            if (currentPage.value - 1) {
                currentPage.setValue(numberOfPages - 1)
                return
            }
            currentPage.setValue(currentPage.value - 1);
        },
        child: Widget.Box({
            orientation: Gtk.Orientation.VERTICAL,
            children: [
                stack,
                Widget.Box({
                    children: dotButtons,
                    class_name: "dotbuttons_box",
                    halign: Gtk.Align.CENTER,
                })
            ]
        })
    })
}
