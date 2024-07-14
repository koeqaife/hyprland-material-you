import { Gtk as GtkType } from "types/@girs/gtk-3.0/gtk-3.0";
import { Notification as NotificationType } from "types/service/notifications";
import Box from "types/widgets/box";
import { timeout } from "resource:///com/github/Aylur/ags/utils.js";
import GLib from "gi://GLib";
import Pango from "gi://Pango";
import Label from "types/widgets/label";
import { MaterialIcon } from "icons";

const notifications = await Service.import("notifications");
import Gtk from "gi://Gtk?version=3.0";

function NotificationIcon({ app_entry, app_icon, image }: NotificationType): Box<GtkType.Widget, any> {
    if (image) {
        return Widget.Box({
            css:
                `background-image: url("${image}");` +
                "background-size: contain;" +
                "background-repeat: no-repeat;" +
                "background-position: center;"
        });
    }

    let icon = "dialog-information-symbolic";
    if (Utils.lookUpIcon(app_icon)) icon = app_icon;

    if (app_entry && Utils.lookUpIcon(app_entry)) icon = app_entry;

    return Widget.Box({
        child: Widget.Icon(icon)
    });
}

export const Notification = (notification: NotificationType, dismiss = true) =>
    Widget.Box({
        class_name: `notification ${notification.urgency}`,
        vertical: true,
        children: [
            Widget.EventBox({
                on_primary_click: (box) => {
                    // @ts-expect-error
                    const label: Label<any> = box.child.children[1]!.children[1]!;
                    if (label.lines < 0) {
                        label.lines = 3;
                        label.truncate = "end";
                    } else {
                        label.lines = -1;
                        label.truncate = "none";
                    }
                },
                child: Widget.Box({
                    children: [
                        Widget.Box({
                            class_name: "notification-icon",
                            child: NotificationIcon(notification),
                            vpack: "start"
                        }),
                        Widget.Box({
                            vertical: true,
                            children: [
                                Widget.Box({
                                    children: [
                                        Widget.Label({
                                            class_name: "notification-title",
                                            label: notification.summary,
                                            justification: "left",
                                            max_width_chars: 3,
                                            truncate: "end",
                                            lines: 1,
                                            xalign: 0,
                                            hexpand: true,
                                            tooltip_text: notification.summary
                                        }),
                                        Widget.Label({
                                            class_name: "notification-time",
                                            label: GLib.DateTime.new_from_unix_local(notification.time).format("%H:%M")
                                        }),
                                        Widget.Button({
                                            class_name: "standard_icon_button notification-close",
                                            child: MaterialIcon("close"),
                                            on_clicked: () => {
                                                if (dismiss) {
                                                    notification.dismiss();
                                                } else {
                                                    notification.close();
                                                }
                                            },
                                            css: "margin-left: 5px;"
                                        })
                                    ]
                                }),
                                Widget.Label({
                                    class_name: "notification-body",
                                    justification: "left",
                                    max_width_chars: 24,
                                    lines: 3,
                                    truncate: "end",
                                    wrap_mode: Pango.WrapMode.WORD_CHAR,
                                    xalign: 0,
                                    wrap: true,
                                    label: notification.body.replace(/(\r\n|\n|\r)/gm, " ")
                                }),
                                notification.hints.value
                                    ? Widget.ProgressBar({
                                          class_name: "notification-progress",
                                          value: Number(notification.hints.value.unpack()) / 100
                                      })
                                    : Widget.Box()
                            ]
                        })
                    ]
                })
            }),
            Widget.Box({
                hpack: "end",
                class_name: "notification-actions",
                children: notification.actions.map((action) =>
                    Widget.Button({
                        child: Widget.Label(action.label),
                        on_clicked: () => notification.invoke(action.id),
                        class_name: "notification-action-button"
                    })
                )
            })
        ]
    });

const NotificationReveal = (notification: NotificationType, visible = false, dismiss = true) => {
    const transition_duration = 200;
    const secondRevealer = Widget.Revealer({
        vpack: "start",
        child: Notification(notification, dismiss),
        reveal_child: visible,
        transition: "slide_left",
        transition_duration: transition_duration,
        hexpand: true,
        class_name: "second_revealer",
        setup: (revealer) => {
            timeout(1, () => {
                revealer.reveal_child = true;
            });
        }
    });

    const firstRevealer = Widget.Revealer({
        child: secondRevealer,
        reveal_child: true,
        transition: "slide_down",
        transition_duration: transition_duration,
        class_name: "first_revealer"
    });

    type BoxAttrs = {
        destroyWithAnims: any;
        count: number;
        id: number;
        app: string;
        destroying: boolean;
    };

    let box: Box<any, BoxAttrs>;

    const destroyWithAnims = () => {
        box.attribute.destroying = true;
        secondRevealer.reveal_child = false;
        timeout(transition_duration, () => {
            firstRevealer.reveal_child = false;
            timeout(transition_duration, () => {
                box.destroy();
            });
        });
    };
    box = Widget.Box({
        hexpand: true,
        hpack: "end",
        attribute: {
            destroyWithAnims: destroyWithAnims,
            count: 0,
            id: notification.id,
            app: notification.app_name,
            destroying: false
        },
        children: [firstRevealer]
    });
    return box;
};

type NotificationsBoxType = {
    exclude: string[];
    include: string[];
};

export function NotificationPopups(
    dismiss = true,
    { exclude, include }: NotificationsBoxType = { exclude: [], include: [] },
    timeout = true,
    revealer = NotificationReveal
) {
    const list = Widget.Box({
        vpack: "start",
        vertical: true,
        children: notifications.popups.map((id) => revealer(id, false, dismiss))
    });

    function onChange() {
        for (let i = 0; i < list.children.length; i++) {
            const current = list.children[i];
            const next = list.children[i + 1];
            const prev = list.children[i - 1];
            let is_last = true;
            let is_first = true;
            let margin_bottom = false;
            if (next && !next?.attribute.destroying) {
                if (next.attribute.app === current.attribute.app) {
                    is_last = false;
                }
            }
            if (prev && !prev?.attribute.destroying) {
                if (prev.attribute.app === current.attribute.app) {
                    is_first = false;
                }
            }
            if (next) {
                if (!(next.attribute.app === current.attribute.app)) {
                    margin_bottom = true;
                }
            }
            current.toggleClassName("last", is_last);
            current.toggleClassName("margin_bottom", margin_bottom);
            current.toggleClassName("first", is_first);
            current.toggleClassName("middle", !is_first && !is_last);
        }
    }

    function onNotified(_: any, id: number) {
        const n = notifications.getNotification(id);
        if (notifications.dnd || !n) return;
        if (exclude.includes(n.app_name.trim())) return;
        if (!include.includes(n.app_name.trim()) && include.length > 0) return;
        const original = list.children.find((n) => n.attribute.id === id);
        const replace = original?.attribute.id;
        let notification;
        if (!replace) {
            notification = revealer(n, false, dismiss);
            notification.attribute.count = 1;
            list.pack_end(notification, false, false, 0);
        } else if (original) {
            notification = revealer(n, true, dismiss);
            notification.attribute.count++;
            original.destroy();
            list.pack_end(notification, false, false, 0);
        }
        if (timeout)
            Utils.timeout(7500, () => {
                if (notification !== null && !notification.disposed) {
                    onDismissed(_, id);
                }
            });
        onChange();
    }

    function onDismissed(_: any, id: number) {
        const original = list.children.find((n) => n.attribute.id === id);
        if (!original) return;
        original.attribute.count--;
        if (original.attribute.count <= 0) {
            original.attribute.destroyWithAnims();
        }
        onChange();
        original.connect("destroy", () => onChange());
    }

    list.hook(notifications, onNotified, "notified").hook(notifications, onDismissed, dismiss ? "dismissed" : "closed");
    return list;
}

export function Notifications(monitor = 0) {
    const window = Widget.Window({
        monitor,
        name: `notifications${monitor}`,
        class_name: "notification-popups",
        anchor: ["top", "right"],
        type: Gtk.WindowType.POPUP,
        child: Widget.Box({
            css: "min-width: 2px; min-height: 2px;",
            class_name: "notifications",
            hexpand: true,
            vexpand: true,
            child: NotificationPopups()
        }),
        visible: true
    });
    return window;
}
