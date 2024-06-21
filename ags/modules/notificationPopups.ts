import { Gtk as GtkType } from "types/@girs/gtk-3.0/gtk-3.0";
import { Notification as NotificationType } from "types/service/notifications";
import Box from "types/widgets/box";
import Window from "types/widgets/window";

const notifications = await Service.import("notifications")
const { Gtk } = imports.gi;

function NotificationIcon({ app_entry, app_icon, image }: NotificationType): Box<GtkType.Widget, any> {
    if (image) {
        return Widget.Box({
            css: `background-image: url("${image}");`
                + "background-size: contain;"
                + "background-repeat: no-repeat;"
                + "background-position: center;",
        })
    }

    let icon = "dialog-information-symbolic"
    if (Utils.lookUpIcon(app_icon))
        icon = app_icon

    if (app_entry && Utils.lookUpIcon(app_entry))
        icon = app_entry

    return Widget.Box({
        child: Widget.Icon(icon),
    })
}


function Notification(n: NotificationType) {
    const icon = Widget.Box({
        vpack: "start",
        class_name: "notification-icon",
        child: NotificationIcon(n),
    })

    const title = Widget.Label({
        class_name: "notification-title",
        xalign: 0,
        justification: "left",
        hexpand: true,
        max_width_chars: 24,
        truncate: "end",
        wrap: true,
        label: n.summary,
        use_markup: true,
    })

    const body = Widget.Label({
        class_name: "notification-body",
        hexpand: true,
        use_markup: true,
        xalign: 0,
        justification: "left",
        label: n.body,
        wrap: true,
    })

    const actions = Widget.Box({
        halign: Gtk.Align.END,
        class_name: "notification-actions",
        children: n.actions.map(({ id, label }) => Widget.Button({
            class_name: "notification-action-button",
            on_clicked: () => {
                n.invoke(id)
                n.dismiss()
            },
            hexpand: false,
            child: Widget.Label(label),
        })),
    })

    return Widget.EventBox(
        {
            attribute: { id: n.id },
            on_secondary_click: n.dismiss,
        },
        Widget.Box(
            {
                class_name: `notification ${n.urgency}`,
                vertical: true,
            },
            Widget.Box([
                icon,
                Widget.Box(
                    { vertical: true },
                    title,
                    body,
                ),
            ]),
            actions,
        ),
    )
}

export function NotificationPopups(monitor = 0) {
    let window: Window<any, any>;
    const list = Widget.Box({
        vertical: true,
        children: notifications.popups.map(Notification),
    })

    const updateWindowSize = () => {
        const [minHeight, naturalHeight] = list.get_preferred_height();
        const [minWidth, naturalWidth] = list.get_preferred_width();

        if (naturalHeight > 0 && naturalWidth > 0) {
            window.set_default_size(minWidth, minHeight);
            window.resize(naturalWidth, naturalHeight);
            window.set_visible(true);
        } else {
            window.set_visible(false);
        }
    };

    function onNotified(_: any, id: number) {
        const n = notifications.getNotification(id)
        if (n) {

            if (notifications.dnd) {
                n.dismiss()
            }
            else {
                list.children = [Notification(n), ...list.children]
                updateWindowSize()
                setTimeout(() => {
                    n.dismiss()
                }, 15000)
            }
        }
    }

    function onDismissed(_: any, id: number) {
        list.children.find(n => n.attribute.id === id)?.destroy()
        updateWindowSize()
    }

    list.hook(notifications, onNotified, "notified")
        .hook(notifications, onDismissed, "dismissed")

    window =  Widget.Window({
        monitor,
        name: `notifications${monitor}`,
        class_name: "notification-popups",
        anchor: ["top", "right"],
        type: Gtk.WindowType.POPUP,
        child: Widget.Box({
            css: "min-width: 2px; min-height: 2px;",
            class_name: "notifications",
            children: [
                list
            ],
        }),
        visible: false,
    })
    return window
}