// by koeqaife ;)

import { type BluetoothDevice } from "types/service/bluetooth";
import Revealer from "types/widgets/revealer";

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

const DeviceItem = (_device: BluetoothDevice) => {
    let device = _device;
    const icon = Widget.Icon({
        icon: `${device.icon_name}-symbolic`,
        hpack: "center",
        vpack: "center",
        size: 20
    });
    const info = Widget.Box({
        vertical: true,
        vpack: "center",
        children: [
            Widget.Label({
                class_name: "title",
                label: device.name.trim(),
                hpack: "start"
            }),
            Widget.Revealer({
                child: Widget.Label({
                    class_name: "description",
                    label: "",
                    hpack: "start"
                }),
                reveal_child: false
            })
        ]
    });
    const button = Widget.Button({
        class_name: "row",
        on_primary_click_release: () => {
            if (bluetooth.enabled) device.setConnection(!device.connected);
        },
        on_secondary_click_release: (self, event) => {
            DeviceMenu(device)?.popup_at_pointer(event);
        },
        child: Widget.Box({
            class_name: "device_box",
            children: [icon, info]
        }),
        attribute: {
            address: device.address,
            update: (_device: BluetoothDevice) => {
                device = _device;
                button.attribute.address = device.address;
                icon.icon = `${device.icon_name}-symbolic`;

                const description_revealer = info.children[1] as Revealer<any, any>;
                const description = description_revealer.child;
                if (device.connected) {
                    description.label = "Active";
                    description_revealer.reveal_child = true;
                } else if (device.connecting) {
                    description.label = "Connecting...";
                    description_revealer.reveal_child = true;
                } else {
                    description_revealer.reveal_child = false;
                }
                button.toggleClassName("active", device.connected);
            }
        }
    });
    button.attribute.update(device);
    return button;
};

function DeviceList() {
    return Widget.Box({
        vertical: true,
        attribute: {
            updateDeviceList: (self) => {
                let devices = bluetooth.devices || [];

                devices = devices.filter((device) => device.name !== null);

                devices.forEach((device) => {
                    const existing_deice = self.children.find(
                        (child) => child.attribute.address === device.address && device.name !== null
                    );

                    if (existing_deice) {
                        existing_deice.attribute.update(device);
                    } else if (existing_deice?.name !== null) {
                        self.pack_start(DeviceItem(device), false, false, 0);
                    }
                });

                self.children = self.children.filter((child: any) =>
                    devices.find((ap) => ap.address === child.attribute.address)
                );
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
