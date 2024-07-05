import { Notification as NotificationType } from "types/service/notifications";
import { NotificationPopups, Notification } from "modules/notificationPopups";
import Box from "types/widgets/box";

const notifications = await Service.import("notifications")

type NotificationsBoxType = {
    exclude?: string[],
    include?: string[]
}

const NotificationNoReveal = (notification: NotificationType, visible = false, dismiss = true) => {
    type BoxAttrs = {
        destroyWithAnims: any,
        count: number,
        id: number,
    }

    const _notification = Notification(notification, dismiss);

    let box: Box<any, BoxAttrs>;

    const destroyWithAnims = () => {
        box.destroy();
    };
    box = Widget.Box({
        hexpand: true,
        attribute: {
            "destroyWithAnims": destroyWithAnims,
            count: 0,
            id: notification.id,
        },
        children: [_notification],
    });
    return box;
};

export function NotificationsBox({ exclude = [], include = [] }: NotificationsBoxType) {
    const popups = NotificationPopups(
        false, { exclude: exclude, include: include },
        false, NotificationNoReveal
    );

    const menu = Widget.Menu({
        class_name: "notifications_menu",
        children: [
            Widget.MenuItem({
                child: Widget.Label({
                    label: "Close all",
                    hpack: "start"
                }),
                class_name: "notifications_menu_item",
                on_activate: () => {
                    for (let n of notifications.notifications) {
                        if (n) {
                            n.dismiss()
                            n.close()
                        }
                    }
                }
            }),
        ],
    })

    return Widget.EventBox({
        vexpand: true,
        hexpand: true,
        on_secondary_click_release: (_, event) => {
            menu.popup_at_pointer(event)
        },
        child: Widget.Scrollable({
            class_name: "notifications_sidebar_scrollable",
            hscroll: "never",
            child: popups,
            hexpand: true
        }),
    })
}
