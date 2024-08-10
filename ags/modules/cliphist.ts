const WINDOW_NAME = "cliphist";
import popupwindow from "./misc/popupwindow.ts";
import Gtk from "gi://Gtk?version=3.0";
import { MaterialIcon } from "icons";

type EntryObject = {
    id: string;
    content: string;
    entry: string;
};

const binary_data = /\[\[ binary data (\d+) (KiB|MiB) (\w+) (\d+)x(\d+) \]\]/;

function ClipHistItem(entry: string) {
    let [id, ..._content] = entry.split("\t");
    let content = _content.join(" ").trim();
    const matches = content.match(binary_data);
    let _show_image = false;

    let clickCount = 0;
    let button = Widget.Button({
        class_name: "clip_container",
        child: Widget.Box({
            children: [
                Widget.Label({
                    label: id,
                    class_name: "clip_id",
                    xalign: 0,
                    vpack: "center"
                }),
                Widget.Label({
                    label: "・",
                    class_name: "dot_divider",
                    xalign: 0,
                    vpack: "center"
                }),
                Widget.Label({
                    label: content,
                    class_name: "clip_label",
                    xalign: 0,
                    vpack: "center",
                    truncate: "end"
                })
            ]
        })
    });

    function show_image(file: string, width: string | number, height: string | number) {
        if (_show_image) return;
        const box = button.child;
        box.children[2].destroy();
        const icon = Widget.Box({
            vpack: "center",
            css: (() => {
                const _widthPx = Number(width);
                const heightPx = Number(height);
                const maxWidth = 400;
                const widthPx = (_widthPx / heightPx) * 150;

                let css = `background-image: url("${file}");`;

                if (widthPx > maxWidth) {
                    const newHeightPx = (150 / widthPx) * maxWidth;
                    css += `min-height: ${newHeightPx}px; min-width: ${maxWidth}px;`;
                } else {
                    css += `min-height: 150px; min-width: ${widthPx}px;`;
                }

                return css;
            })(),
            class_name: "preview"
        });
        // @ts-expect-error
        box.children = [...box.children, icon];
        _show_image = true;
    }

    function hide_image() {
        if (!_show_image) return;
        const box = button.child;
        box.children[2].destroy();
        const label = Widget.Label({
            label: content,
            class_name: "clip_label",
            xalign: 0,
            vpack: "center",
            truncate: "end"
        });
        box.children = [...box.children, label];
        _show_image = false;
    }

    button.connect("clicked", () => {
        clickCount++;
        if (clickCount === 2) {
            App.closeWindow(WINDOW_NAME);
            Utils.execAsync(`${App.configDir}/scripts/cliphist.sh --copy-by-id ${id}`);
            clickCount = 0;
        }
    });
    if (matches) {
        // const size = matches[1];
        const format = matches[3];
        const width = matches[4];
        const height = matches[5];
        if (format == "png") {
            button.toggleClassName("with_image", true);
            button.connect("clicked", () => {
                if (!_show_image) {
                    Utils.execAsync(`${App.configDir}/scripts/cliphist.sh --save-by-id ${id}`)
                        .then((file) => {
                            show_image(file, width, height);
                            Utils.exec(`rm -f /tmp/ags/cliphist/${id}.png`);
                        })
                        .catch(print);
                }
            });
        }
    }

    button.connect("focus-out-event", () => {
        clickCount = 0;
    });

    return Widget.Box({
        attribute: { content: content, id: id, hide_image: hide_image, show_image: show_image },
        orientation: Gtk.Orientation.VERTICAL,
        visible: true,
        children: [
            button,
            Widget.Separator({
                class_name: "clip_divider",
                orientation: Gtk.Orientation.HORIZONTAL
            })
        ]
    });
}

function ClipHistWidget({ width = 500, height = 500, spacing = 12 }) {
    let output: string;
    let entries: string[];
    let clipHistItems: EntryObject[];

    const list = Widget.Box<ReturnType<typeof ClipHistItem>, unknown>({
        vertical: true
    });

    async function repopulate() {
        output = await Utils.execAsync(`${App.configDir}/scripts/cliphist.sh --get`)
            .then((str) => str)
            .catch((err) => {
                print(err);
                return "";
            });
        entries = output.split("\n").filter((line) => line.trim() !== "");
        clipHistItems = entries.map((entry) => {
            let [id, ...content] = entry.split("\t");
            return { id: id.trim(), content: content.join(" ").trim(), entry: entry };
        });

        const widget_ids = new Set(clipHistItems.map((item) => item.id));
        for (const item of list.children) {
            if (!widget_ids.has(item.attribute.id)) {
                item.destroy();
            }
        }

        const list_ids = new Set(list.children.map((item) => item.attribute.id));
        for (const item of clipHistItems) {
            if (!list_ids.has(item.id)) {
                const _item = ClipHistItem(item.entry);
                list.pack_end(_item, false, false, 0);
            }
        }
        list.children = list.children.sort((a, b) => Number(a.attribute.id) - Number(b.attribute.id)).reverse();
    }
    repopulate();

    const entry = Widget.Entry({
        hexpand: true,
        class_name: "cliphistory_entry",
        placeholder_text: "Search",
        vpack: "center",

        on_change: ({ text }) => {
            const searchText = (text ?? "").toLowerCase();
            list.children.forEach((item) => {
                item.visible = item.attribute.content.toLowerCase().includes(searchText);
            });
        }
    });

    const clearButton = Widget.Button({
        child: MaterialIcon("delete_forever"),
        class_name: "filled_tonal_button clear_button",
        vpack: "center",
        on_clicked: () => {
            Utils.execAsync(`${App.configDir}/scripts/cliphist.sh --clear`)
                .then(() => {
                    repopulate().catch(print);
                })
                .catch(print);
        }
    });

    const searchBox = Widget.Box({
        orientation: Gtk.Orientation.HORIZONTAL,
        children: [entry, clearButton]
    });

    return Widget.Box({
        orientation: Gtk.Orientation.VERTICAL,
        class_name: "cliphistory_box",
        margin_top: 14,
        margin_right: 14,
        children: [
            searchBox,
            Widget.Separator(),
            Widget.Scrollable({
                hscroll: "never",
                css: `min-width: ${width}px;` + `min-height: ${height}px;`,
                child: list
            })
        ],
        setup: (self) =>
            self.hook(App, (_, windowName, visible) => {
                if (windowName !== WINDOW_NAME) return;

                if (visible) {
                    repopulate().catch(print);
                    entry.text = "";
                } else {
                    for (const item of list.children) {
                        item.attribute.hide_image();
                    }
                }
            })
    });
}

export const cliphist = popupwindow({
    name: WINDOW_NAME,

    class_name: "cliphistory",
    visible: false,
    keymode: "exclusive",
    child: ClipHistWidget({
        width: 500,
        height: 500,
        spacing: 0
    }),
    anchor: ["top", "right"]
});
