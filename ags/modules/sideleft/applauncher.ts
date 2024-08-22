const { query } = await Service.import("applications");
const encoder = new TextEncoder();
const decoder = new TextDecoder();
const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;
import Box from "types/widgets/box";
import Gtk from "gi://Gtk?version=3.0";
import { Application } from "types/service/applications";
import { WINDOW_NAME } from "modules/sideleft/main";

const LAUNCH_COUNT_FILE = Gio.File.new_for_path(
    GLib.build_filenamev([GLib.get_home_dir(), ".cache", "launch_counts.json"])
);

function read_launch_counts() {
    try {
        if (!LAUNCH_COUNT_FILE.query_exists(null)) {
            return {};
        }
        const [, contents] = LAUNCH_COUNT_FILE.load_contents(null);
        return JSON.parse(decoder.decode(contents));
    } catch (error) {
        return {};
    }
}

function write_launch_counts(launchCounts: number) {
    const data = JSON.stringify(launchCounts, null, 2);
    LAUNCH_COUNT_FILE.replace_contents(
        encoder.encode(data),
        null,
        false,
        Gio.FileCreateFlags.REPLACE_DESTINATION,
        null
    );
}

function increment_launch_count(appName: string) {
    const launchCounts = read_launch_counts();
    launchCounts[appName] = (launchCounts[appName] || 0) + 1;
    write_launch_counts(launchCounts);
}

function sortApplicationsByLaunchCount(applications: Box<any, any>[]) {
    const launchCounts = read_launch_counts();
    return applications.sort((a: Box<any, any>, b: Box<any, any>) => {
        const countA = launchCounts[a.attribute.app.name] || 0;
        const countB = launchCounts[b.attribute.app.name] || 0;
        return countB - countA;
    });
}

function AppItem(app: Application): Box<any, any> {
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
        })
    });

    button.connect("clicked", () => {
        clickCount++;
        if (clickCount === 2) {
            increment_launch_count(app.name);
            App.closeWindow(WINDOW_NAME);
            app.launch();
            clickCount = 0;
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
}

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

    function repopulate() {
        applications = query("").map(AppItem);
        applications = sortApplicationsByLaunchCount(applications);
        list.children = applications;
    }
    repopulate();

    return Widget.Box({
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
        setup: (self) =>
            self.hook(App, (_, windowName, visible) => {
                if (windowName !== WINDOW_NAME) return;

                if (visible) {
                    repopulate();
                    entry.text = "";
                    entry.grab_focus();
                }
            })
    });
};
