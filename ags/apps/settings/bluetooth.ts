import { type BluetoothDevice } from "types/service/bluetooth";
import Gtk from "gi://Gtk?version=3.0";
import { timeout } from "resource:///com/github/Aylur/ags/utils.js";

const bluetooth = await Service.import("bluetooth");

const HpackStartLabel = (label: string) =>
    Widget.Label({
        label: label,
        hpack: "start"
    });

const BluetoothToggle = () =>
    Widget.EventBox({
        class_name: "row",
        child: Widget.Box({
            class_name: "row",
            children: [
                Widget.Box({
                    vertical: true,
                    vpack: "center",
                    hexpand: true,
                    children: [
                        Widget.Label({
                            hpack: "start",
                            class_name: "title",
                            label: "Enabled"
                        })
                        // Widget.Label({
                        //     hpack: "start",
                        //     class_name: "description",
                        //     label: "Idk"
                        // })
                    ]
                }),
                Widget.Switch({
                    vexpand: false,
                    vpack: "center",
                    hpack: "end",
                    on_activate: (self) => {
                        if (self.state != bluetooth.enabled) bluetooth.enabled = self.state;
                    },
                    state: bluetooth.bind("enabled")
                })
            ]
        }),
        on_primary_click_release: (self) => {
            self.child.children[1]!.activate();
        },
        on_secondary_click_release: (self, event) => {
            Widget.Menu({
                children: [
                    Widget.MenuItem({
                        child: HpackStartLabel("Open blueman-manager"),
                        on_activate: () => {
                            Utils.execAsync("blueman-manager").catch(print);
                        }
                    })
                ]
            }).popup_at_pointer(event);
        }
    });

const DeviceMenu = (device: BluetoothDevice) => {
    if (device.connecting) {
        return undefined;
    }
    return Widget.Menu({
        children: [
            !device.connected
                ? Widget.MenuItem({
                      child: HpackStartLabel("Connect"),
                      on_activate: () => {
                          device.setConnection(true);
                      }
                  })
                : Widget.MenuItem({
                      child: HpackStartLabel("Disconnect"),
                      on_activate: () => {
                          device.setConnection(false);
                      }
                  }),
            Widget.MenuItem({
                child: HpackStartLabel("Copy Address"),
                on_activate: () => {
                    Utils.execAsync(["wl-copy", device.address]);
                }
            })
        ]
    });
};

const DeviceItem = (device: BluetoothDevice) =>
    Widget.Button({
        class_name: "row",
        on_primary_click_release: () => {
            device.setConnection(!device.connected);
        },
        on_secondary_click_release: (self, event) => {
            DeviceMenu(device)?.popup_at_pointer(event);
        },
        child: Widget.Box({
            class_name: "device_box",
            children: [
                Widget.Icon({
                    icon: `${device.icon_name}-symbolic`,
                    hpack: "center",
                    vpack: "center",
                    size: 20
                }),
                // @ts-ignore
                Widget.Box({
                    vertical: true,
                    vpack: "center",
                    children: [
                        Widget.Label({
                            class_name: "title",
                            label: device.name.trim(),
                            hpack: "start"
                        }),
                        device.connecting
                            ? Widget.Label({
                                  class_name: "description",
                                  label: device.connected ? "Disconnecting..." : "Connecting...",
                                  hpack: "start"
                              })
                            : device.connected
                            ? Widget.Label({
                                  class_name: "description",
                                  label: "Active",
                                  hpack: "start"
                              })
                            : undefined
                    ]
                })
            ]
        }),

        setup: (self) => {
            self.toggleClassName("active", device.connected);
        }
    });

function DeviceList() {
    return Widget.Box({
        vertical: true,
        attribute: {
            updateDeviceList: (self) => {
                const devices = bluetooth.devices || [];
                self.children = Object.values(devices)
                    .sort((a: BluetoothDevice, b: BluetoothDevice) => {
                        if (a.connected) return -1;
                        if (b.connected) return 1;
                        return 0;
                    })
                    .filter((n: BluetoothDevice) => n.device.name !== null)
                    .map((n: BluetoothDevice) => DeviceItem(n));
            }
        },
        className: "device_list",
        setup: (self) => self.hook(bluetooth, self.attribute.updateDeviceList)
    });
}

export const Bluetooth = () =>
    Widget.Scrollable({
        hscroll: "never",
        child: Widget.Box({
            hexpand: true,
            vexpand: true,
            vertical: true,
            children: [BluetoothToggle(), DeviceList()]
        })
    });
