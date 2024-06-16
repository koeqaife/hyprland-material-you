import Network from "resource:///com/github/Aylur/ags/service/network.js";
import popupwindow from './.widgethacks/popupwindow.js';
const WINDOW_NAME = "wifi";


export const SIGNAL = {
    'network-wireless-signal-excellent-symbolic': "󰤨",
    'network-wireless-signal-good-symbolic': "󰤥",
    'network-wireless-signal-ok-symbolic': "󰤢",
    'network-wireless-signal-weak-symbolic': "󰤟",
    'network-wireless-signal-none-symbolic': "󰤯",
}

// @ts-ignore
let connectAttempt = '';

const WifiNetwork = (accessPoint) => {
    const networkStrength = Widget.Label({
        label: SIGNAL[accessPoint.iconName],
        class_name: "awesome_icon icon",
        css: "margin-right: 0.60em;"
    })
    // @ts-ignore
    const networkName = Widget.Box({
        vertical: true,
        class_name: "network_name",
        children: [
            Widget.Label({
                hpack: 'start',
                label: accessPoint.ssid
            })
        ]
    });
    return Widget.Button({
        onClicked: accessPoint.active ? () => { } : () => Utils.execAsync(`nmcli device wifi connect ${accessPoint.bssid}`)
            // .catch(e => {
            //     Utils.notify({
            //         summary: "Network",
            //         body: e,
            //         actions: { "Open network manager": () => Utils.execAsync("nm-connection-editor").catch(print) }
            //     });
            // })
            .catch(print),
        className: 'wifi_button',
        // @ts-ignore
        child: Widget.Box({
            className: 'wifi_Box',
            children: [
                networkStrength,
                networkName,
                Widget.Box({ hexpand: true }),
                accessPoint.active ? Widget.Label({
                    label: "",
                    class_name: "awesome_icon icon"
                }) : null,
            ],
        })
    })
}


const CurrentNetwork = () => {
    let authLock = false;
    // console.log(Network.wifi);
    const networkName = Widget.Box({
        vertical: true,
        hexpand: true,
        children: [
            Widget.Label({
                hpack: 'start',
                className: 'wifi_current',
                label: "Current network:",
            }),
            Widget.Label({
                hpack: 'start',
                className: 'wifi_ssid',
                label: Network.wifi?.ssid,
                setup: (self) => self.hook(Network, (self) => {
                    if (authLock) return;
                    // @ts-ignore
                    self.label = Network.wifi?.ssid;
                }),
            }),
        ]
    });
    const networkStatus = Widget.Box({
        className: 'wifi_status',
        children: [Widget.Label({
            vpack: 'center',
            setup: (self) => self.hook(Network, (self) => {
                if (authLock) return;
                self.label = Network.wifi.state;
            }),
        })]
    })
    const networkAuth = Widget.Revealer({
        transition: 'slide_down',
        transitionDuration: 400,
        child: Widget.Box({
            className: 'wifi_revealer_box',
            vertical: true,
            children: [
                Widget.Label({
                    hpack: 'start',
                    label: "Authentication",
                }),
                Widget.Entry({
                    visibility: false, // Password dots
                    onAccept: (self) => {
                        authLock = false;
                        networkAuth.revealChild = false;
                        Utils.execAsync(`nmcli device wifi connect '${connectAttempt}' password '${self.text}'`)
                            .catch(print);
                    }
                })
            ]
        }),
        setup: (self) => self.hook(Network, (self) => {
            if (Network.wifi.state == 'failed' || Network.wifi.state == 'need_auth') {
                authLock = true;
                // @ts-ignore
                connectAttempt = Network.wifi.ssid;
                self.revealChild = true;
            }
            if (Network.wifi.state == "activated") {
                authLock = false;
                self.revealChild = false;
            }
        }),
    });
    const actualContent = Widget.Box({
        vertical: true,
        children: [
            Widget.Box({
                className: 'wifi_actual_content_box',
                vertical: true,
                children: [
                    Widget.Box({
                        children: [
                            networkName,
                            networkStatus,

                        ]
                    }),
                    networkAuth,
                ]
            }),
            // bottomSeparator,
        ]
    });
    return Widget.Box({
        vertical: true,
        children: [Widget.Revealer({
            transition: 'slide_down',
            transitionDuration: 400,
            // @ts-ignore
            revealChild: Network.wifi,
            child: actualContent,
        })]
    })
}

export function WifiWidget(props) {
    const networkList = Widget.Box({
        vertical: true,
        className: 'spacing-v-10',
        children: [
            Widget.Scrollable({
                vexpand: true,
                class_name: "wifi_scrollable",
                child: Widget.Box({
                    class_name: "wifi_scrollable_box",
                    attribute: {
                        'updateNetworks': (self) => {
                            if (Network.wifi.enabled)
                                Utils.execAsync("nmcli device wifi rescan").catch(print)
                            const accessPoints = Network.wifi?.access_points || [];
                            self.children = Object.values(accessPoints.reduce((a, accessPoint) => {
                                // @ts-ignore
                                if (!a[accessPoint.ssid]) {
                                    // @ts-ignore
                                    a[accessPoint.ssid] = accessPoint;
                                    // @ts-ignore
                                    a[accessPoint.ssid].active |= accessPoint.active;
                                }

                                return a;
                            }, {})).map(n => WifiNetwork(n));
                        },
                    },
                    vertical: true,
                    className: 'wifi_list',
                    setup: (self) => self.hook(Network, self.attribute.updateNetworks),
                })
            })
        ]
    })
    return Widget.Box({
        ...props,
        margin: 15,
        className: 'wifi_main_box',
        vertical: true,
        children: [
            CurrentNetwork(),
            networkList
        ]
    });
}

export const wifi = popupwindow({
    name: WINDOW_NAME,

    class_name: "wifi_window",
    visible: false,
    keymode: "exclusive",
    child: WifiWidget(),
    anchor: ["top", "right"]
})
