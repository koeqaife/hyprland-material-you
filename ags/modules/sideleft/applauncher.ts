// by koeqaife ;)

const applications_service = await Service.import("applications");
import Box from "types/widgets/box";
import Gtk from "gi://Gtk?version=3.0";
import { Application } from "types/service/applications";
import { WINDOW_NAME, shown } from "modules/sideleft/main";

const AppItem = (repopulate: () => void) => (app: Application) => {
    let clickCount = 0;
    const button = Widget.Button({
        class_name: "application_container",
        child: Widget.Box({
            children: [
                Widget.Icon({
                    class_name: "application_icon",
                    // @ts-ignore
                    icon: Utils.lookUpIcon(app.icon_name) ? app.icon_name : "image-missing",
                    size: 42
                }),
                Widget.Label({
                    class_name: "application_label",
                    label: app.name,
                    xalign: 0,
                    vpack: "center",
                    truncate: "end"
                })
            ]
        }),
        on_primary_click_release: (self) => {
            clickCount++;
            if (clickCount === 2) {
                App.closeWindow(WINDOW_NAME);
                app.launch();
                repopulate();
                clickCount = 0;
            }
        }
    });

    button.connect("focus-out-event", () => {
        clickCount = 0;
    });

    return Widget.Box({
        attribute: { app },
        orientation: Gtk.Orientation.VERTICAL,
        children: [
            button,
            Widget.Separator({
                class_name: "application_divider",
                orientation: Gtk.Orientation.HORIZONTAL
            })
        ]
    });
};

export const Applauncher = () => {
    let applications: Box<any, any>[];

    const list = Widget.Box({
        vertical: true
    });

    const entry = Widget.Entry({
        hexpand: true,
        class_name: "applauncher_entry",
        placeholder_text: "Search",

        on_accept: () => {
            const results = applications.filter((item) => item.visible);
            if (results[0]) {
                App.closeWindow(WINDOW_NAME);
                results[0].attribute.app.launch();
            }
        },

        on_change: ({ text }) =>
            applications.forEach((item) => {
                item.visible = item.attribute.app.match(text ?? "");
            })
    });

    function reload() {
        applications_service.reload();
        repopulate();
    }

    function repopulate() {
        applications = applications_service.query("").map(AppItem(repopulate));
        list.children = applications;
    }

    const menu = Widget.Menu({
        children: [
            Widget.MenuItem({
                label: "Reload apps",
                on_activate: (self) => {
                    reload();
                }
            })
        ]
    });

    repopulate();

    return Widget.EventBox({
        on_secondary_click_release: (self, event) => {
            menu.popup_at_pointer(event);
        },
        child: Widget.Box({
            vertical: true,
            class_name: "applauncher_box",
            vexpand: true,
            children: [
                entry,
                Widget.Separator(),
                Widget.Scrollable({
                    hscroll: "never",
                    child: list,
                    vexpand: true
                })
            ],
            setup: (self) => {
                self.hook(shown, () => {
                    if (shown.value == "apps") entry.grab_focus();
                });
                self.hook(App, (_, windowName, visible) => {
                    if (windowName !== WINDOW_NAME) return;

                    if (visible) {
                        entry.text = "";
                        entry.grab_focus();
                    }
                });
            }
        })
    });
};
