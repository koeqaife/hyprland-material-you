import { RegularWindow } from "apps/window";
import { MaterialIcon } from "icons";
import Gtk from "gi://Gtk?version=3.0";
import { Variable as VType } from "types/variable";
const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;
const encoder = new TextEncoder();
const decoder = new TextDecoder();

const jsonData = Utils.readFile(`${App.configDir}/assets/emoji.json`);
const hyprland = await Service.import("hyprland");
let current_window;
const current_page = Variable("recent");

const RECENT_EMOJI_FILE = Gio.File.new_for_path(
    GLib.build_filenamev([GLib.get_home_dir(), ".cache", "recent_emoji.json"])
);
const recent = Variable(readRecentEmoji());

function readRecentEmoji() {
    try {
        if (!RECENT_EMOJI_FILE.query_exists(null)) {
            return {};
        }
        const [, contents] = RECENT_EMOJI_FILE.load_contents(null);
        return JSON.parse(decoder.decode(contents));
    } catch (error) {
        return {};
    }
}

function writeRecentEmoji(recent: any) {
    const data = JSON.stringify(recent, null, 2);
    RECENT_EMOJI_FILE.replace_contents(
        encoder.encode(data),
        null,
        false,
        Gio.FileCreateFlags.REPLACE_DESTINATION,
        null
    );
}

function addRecentEmoji(name: string, emoji: string) {
    recent.value[name] = emoji;
    recent.setValue(moveItemsToFront(name, recent.value));
    writeRecentEmoji(recent.value);
}

const emojiData = JSON.parse(jsonData);

function extractEmojis(data) {
    const emojis = {};

    Object.values(data).forEach((subgroup) => {
        // @ts-ignore
        Object.values(subgroup).forEach((emojiGroup) => {
            // @ts-ignore
            Object.entries(emojiGroup).forEach(([key, value]) => {
                emojis[key] = value;
            });
        });
    });

    return emojis;
}

function moveItemsToFront(item: any, arr: any) {
    let new_array = {};
    new_array[item] = arr[item];
    for (let _item in arr) {
        if (_item != item) new_array[_item] = arr[_item];
    }

    return new_array;
}

const CATEGORY_ICONS = {
    "smileys-emotion": "mood",
    "people-body": "emoji_people",
    "animals-nature": "pets",
    "food-drink": "emoji_food_beverage",
    "travel-places": "emoji_transportation",
    activities: "sports_soccer",
    objects: "emoji_objects",
    symbols: "emoji_symbols",
    flags: "flag"
};

export async function OpenEmojiPicker() {
    current_page.setValue("recent");
    if (current_window) {
        const _current_workspace = hyprland.active.workspace.id;
        const _client = hyprland.clients.find((client) => {
            return client.class == "com.github.Aylur.ags" && client.title == "Emoji Picker";
        });
        if (_client && _current_workspace != _client.workspace.id) {
            current_window.hide();
            current_window.show();
        } else current_window.show();
    } else EmojisWindow();
}

globalThis.OpenEmojiPicker = OpenEmojiPicker;

function searchString(str: string, keywords: string) {
    const searchTerms = keywords.split(" ");

    for (let term of searchTerms) {
        if (!str.toLowerCase().includes(term.toLowerCase())) {
            return false;
        }
    }

    return true;
}

function RecentPage() {
    const emojiList = extractEmojis(emojiData);
    const box = Widget.Box({
        vertical: true,
        vexpand: true,
        vpack: "start"
    });
    box.hook(recent, (self) => {
        Utils.idle(() => {
            const flow = Widget.FlowBox({
                homogeneous: true
            });
            flow.set_min_children_per_line(5);
            flow.set_max_children_per_line(25);
            for (const emojiKey in recent.value) {
                let emoji = emojiList[emojiKey];
                flow.add(
                    Widget.Button({
                        class_name: "standard_icon_button emoji",
                        label: emoji,
                        attribute: { emoji: emoji },
                        on_clicked: (self) => {
                            Utils.execAsync(`wl-copy ${self.attribute.emoji}`).catch(print);
                            current_window.hide();
                        },
                        tooltipText: emojiKey
                            .replace(/^e\d+-\d+/, "")
                            .replaceAll("-", " ")
                            .trim()
                    })
                );
            }
            box.child = flow;
        });
    });

    return Widget.Scrollable({
        child: box,
        hscroll: "never",
        vexpand: true
    });
}

function SearchPage(search: VType<string>) {
    const emojiList = extractEmojis(emojiData);
    const box = Widget.Box({
        vertical: true,
        vexpand: true,
        vpack: "start"
    });
    box.hook(search, (self) => {
        Utils.idle(() => {
            if (search.value.length == 0) return;
            const flow = Widget.FlowBox({
                homogeneous: true
            });
            flow.set_min_children_per_line(5);
            flow.set_max_children_per_line(25);
            for (const emojiKey in emojiList) {
                let emoji = emojiList[emojiKey];
                if (searchString(emojiKey, search.value))
                    flow.add(
                        Widget.Button({
                            class_name: "standard_icon_button emoji",
                            label: emoji,
                            attribute: { emoji: emoji },
                            on_clicked: (self) => {
                                Utils.execAsync(`wl-copy ${self.attribute.emoji}`).catch(print);
                                current_window.hide();
                            },
                            tooltipText: emojiKey
                                .replace(/^e\d+-\d+/, "")
                                .replaceAll("-", " ")
                                .trim()
                        })
                    );
            }
            box.child = flow;
        });
    });

    return Widget.Scrollable({
        child: box,
        hscroll: "never",
        vexpand: true
    });
}

function Page(category) {
    const box = Widget.Box({
        vertical: true,
        vexpand: true,
        vpack: "start"
    });
    for (let subcategoryKey in category) {
        box.pack_start(
            Widget.Label({
                label: subcategoryKey.charAt(0).toUpperCase() + subcategoryKey.replaceAll("-", " ").slice(1) + ":",
                class_name: "title",
                vpack: "start",
                hpack: "start"
            }),
            false,
            false,
            0
        );
        const flow = Widget.FlowBox({
            homogeneous: true
        });
        flow.set_min_children_per_line(5);
        flow.set_max_children_per_line(25);
        let emojis = category[subcategoryKey];
        for (let emojiKey in emojis) {
            let emoji = emojis[emojiKey];
            flow.add(
                Widget.Button({
                    class_name: "standard_icon_button emoji",
                    label: emoji,
                    attribute: { emoji: emoji },
                    on_clicked: (self) => {
                        addRecentEmoji(emojiKey, emoji);
                        Utils.execAsync(`wl-copy ${self.attribute.emoji}`).catch(print);
                        current_window.hide();
                    },
                    tooltipText: emojiKey
                        .replace(/^e\d+-\d+/, "")
                        .replaceAll("-", " ")
                        .trim()
                })
            );
        }
        box.pack_start(flow, false, false, 0);
    }
    return Widget.Scrollable({
        child: box,
        hscroll: "never",
        vexpand: true
    });
}

function EmojiList() {
    const search = Variable("");
    const Button = (icon: string, name: string) =>
        Widget.Button({
            class_name: "emoji_category standard_icon_button",
            child: MaterialIcon(icon),
            setup: (self) => {
                self.hook(current_page, () => {
                    self.toggleClassName("active", current_page.value == name);
                });
            },
            on_clicked: () => {
                current_page.setValue(name);
            }
        });

    let categories_pages = {
        search: SearchPage(search),
        recent: RecentPage()
    };
    let categories_buttons = [Button("schedule", "recent")];
    for (const name in emojiData) {
        categories_buttons = [...categories_buttons, Button(CATEGORY_ICONS[name]!, name)];
        categories_pages[name] = Page(emojiData[name]);
    }

    const stack = Widget.Stack({
        children: categories_pages,
        setup: (self) => {
            self.hook(current_page, () => {
                if (self.shown == "search") {
                    entry.text = "";
                }
                // @ts-ignore
                self.shown = current_page.value;
            });
            self.hook(search, () => {
                if (self.shown != "search" && search.value.length > 0) {
                    self.shown = "search";
                } else if (search.value.length == 0) {
                    // @ts-ignore
                    self.shown = current_page.value;
                }
            });
        },
        transition: "crossfade"
    });
    const entry = Widget.Entry({
        placeholder_text: "Search",
        class_name: "search",
        on_change: (self) => {
            search.setValue(entry.text!);
        }
    });

    const box = Widget.Box({
        class_name: "emoji_list",
        vertical: true,
        children: [
            Widget.Scrollable({
                vscroll: "never",
                hscroll: "always",
                child: Widget.Box({
                    class_name: "top_bar",
                    children: [entry, ...categories_buttons]
                })
            }),
            stack
        ]
    });

    return box;
}

export const EmojisWindow = () => {
    let window = RegularWindow({
        title: "Emoji Picker",
        default_height: 600,
        default_width: 400,
        class_name: "emojis",
        child: EmojiList(),
        setup(win: any) {
            current_window = win;
            win.keybind("Escape", () => {
                win.close();
            });
        },
        visible: true
    });
    // @ts-ignore
    window.on("delete-event", () => {
        // @ts-ignore
        window.hide();
        return true;
    });

    return window;
};
