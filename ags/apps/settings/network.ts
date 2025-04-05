// by koeqaife ;)

import { timeout } from "resource:///com/github/Aylur/ags/utils.js";
import { MaterialIcon } from "icons";
const systemtray = await Service.import("systemtray");
const network = await Service.import("network");
import { current_tab, saved_networks, current_window } from "./variables";
import Box from "types/widgets/box";
import Revealer from "types/widgets/revealer";

const WIFI_ICONS = {
    "network-wireless-signal-excellent-symbolic": "signal_wifi_4_bar",
    "network-wireless-signal-good-symbolic": "network_wifi_3_bar",
    "network-wireless-signal-ok-symbolic": "network_wifi_2_bar",
    "network-wireless-signal-weak-symbolic": "network_wifi_1_bar",
    "network-wireless-signal-none-symbolic": "signal_wifi_0_bar"
};

type AccessPoint = {
    bssid: string | null;
    address: string | null;
    lastSeen: number;
    ssid: string | null;
    active: boolean;
    strength: number;
    frequency: number;
    iconName: string | undefined;
};

Utils.interval(15000, () => {
    if (current_tab.value != "network" || !current_window?.visible) return;
    if (!network.wifi.enabled) return;
    wifi_scan();
});

const network_state = {
    unavailable: "Device is unavailable",
    disconnected: "Device is disconnected",
    prepare: "Preparing to connect...",
    config: "Configuring connection...",
    need_auth: "Authentication required...",
    ip_config: "Obtaining IP address...",
    ip_check: "Verifying IP address...",
    secondaries: "Setting up secondary connections...",
    activated: "Connected",
    deactivating: "Disconnecting...",
    failed: "Connection failed"
};

function wifi_scan() {
    try {
        network.wifi?.scan();
    } catch (error) {
        print(error);
    }
}

const WifiNetwork = (access_point: AccessPoint) => {
    const connected = () => access_point.ssid == network.wifi.ssid;
    const saved = () => saved_networks.value.includes(access_point.ssid!);

    const icon = MaterialIcon(WIFI_ICONS[access_point.iconName!], "20px");
    const info = Widget.Box({
        vertical: true,
        vpack: "center",
        children: [
            Widget.Label({
                class_name: "title",
                label: access_point.ssid,
                hpack: "start",
                vpack: "center"
            }),
            Widget.Revealer({
                child: Widget.Label({
                    class_name: "description",
                    label: "",
                    hpack: "start",
                    visible: true
                }),
                reveal_child: false
            })
        ]
    });
    const button = Widget.Button({
        class_name: "row",
        on_primary_click_release: () => {
            if (!connected()) Utils.execAsync(`nmcli device wifi connect '${access_point.ssid}'`).catch(print);
        },
        on_secondary_click_release: () => {
            Utils.execAsync(`${App.configDir}/scripts/network.sh --edit ${access_point.ssid}`).catch(print);
        },
        attribute: {
            ssid: access_point.ssid,
            update: (access_point: AccessPoint) => {
                button.attribute.ssid = access_point.ssid;
                button.toggleClassName("active", connected());
                icon.set_label(WIFI_ICONS[access_point.iconName!]);

                const description_revealer = info.children[1] as Revealer<any, any>;
                const description = description_revealer.child;
                if (connected()) {
                    description.label = network_state[network.wifi.state];
                    description_revealer.set_reveal_child(true);
                } else if (saved()) {
                    description.label = "Saved";
                    description_revealer.set_reveal_child(true);
                } else {
                    description.label = "";
                    description_revealer.set_reveal_child(false);
                }
            }
        },
        child: Widget.Box({
            class_name: "wifi_network_box",
            children: [icon, info]
        })
    });
    button.attribute.update(access_point);
    return button;
};

const WifiToggle = () =>
    Widget.EventBox({
        class_name: "row",
        child: Widget.Box({
            class_name: "row",
            children: [
                Widget.Box({
                    vertical: true,
                    hexpand: true,
                    children: [
                        Widget.Label({
                            hpack: "start",
                            class_name: "title",
                            label: "Wi-Fi"
                        }),
                        Widget.Label({
                            hpack: "start",
                            class_name: "description",
                            label: "Find and connect to Wi-Fi networks"
                        })
                    ]
                }),
                Widget.Switch({
                    vexpand: false,
                    vpack: "center",
                    hpack: "end",
                    on_activate: (self) => {
                        if (network.wifi.enabled != self.active) network.wifi.enabled = self.active;
                    },
                    active: network.wifi.enabled,
                    setup: (self) => {
                        self.hook(network, () => {
                            if (!network.wifi) return;
                            if (network.wifi.enabled != self.active) self.set_active(network.wifi.enabled ?? false);
                        });
                    }
                })
            ]
        }),
        on_primary_click_release: (self) => {
            self.child.children[1]!.activate();
        }
    });

const WifiList = () => {
    const updateNetwork = (accessPoints: AccessPoint[], self: Box<Box<any, any>, any>) => {
        try {
            const current_ssid = network.wifi?.ssid;

            accessPoints.forEach((accessPoint) => {
                const existing_network = self.children.find((child) => child.attribute.ssid === accessPoint.ssid);

                if (existing_network) {
                    existing_network.attribute.update(accessPoint);
                } else {
                    self.pack_start(WifiNetwork(accessPoint), false, false, 0);
                }
            });

            self.children = self.children.filter((child: any) =>
                accessPoints.find((ap) => ap.ssid === child.attribute.ssid)
            );

            self.children = self.children.sort((a: any, b: any) => {
                if (a.attribute.ssid === current_ssid) return -1;
                if (b.attribute.ssid === current_ssid) return 1;
                return 0;
            });
        } catch (e) {
            print("Error while reloading networks:", e);
        }
    };

    return Widget.Box({
        vertical: true,
        className: "wifi_list",
        attribute: {
            updateNetworks: (self) => {
                const accessPoints = network.wifi?.access_points ?? [];
                updateNetwork(accessPoints, self);
            }
        },
        setup: (self) => {
            self.hook(network.wifi, self.attribute.updateNetworks);
        }
    });
};

const NmAppletRequired = () =>
    Widget.Box({
        class_name: "error_container",
        visible: false,
        hexpand: true,
        child: Widget.Label({
            label: "Requires running nm-applet for authorization when connecting!",
            hpack: "start",
            vpack: "center"
        }),
        setup: (self) => {
            self.hook(systemtray, () => {
                const nm_applet = systemtray.items.find((item) => item.id == "nm-applet");
                if (nm_applet) self.visible = false;
                else self.visible = true;
            });
        }
    });

export function Network() {
    const box = Widget.Box({
        vertical: true,
        children: [NmAppletRequired(), WifiToggle(), WifiList()]
    });
    return Widget.Scrollable({
        hscroll: "never",
        child: box,
        vexpand: true
    });
}
