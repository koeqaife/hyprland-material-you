import Gtk from "gi://Gtk?version=3.0";
import popupwindow from "modules/misc/popupwindow";
import { MaterialIcon } from "icons";
const hyprland = await Service.import("hyprland");

const WINDOW_NAME = "cheatsheet";

const load_keybindings_cmd = `python -OOO ${App.configDir}/scripts/keybindings.py`;
let _keybindings = Utils.exec(load_keybindings_cmd);
const keybindings = Variable(JSON.parse(_keybindings));

// hyprland.connect("event", (hyprland, name) => {
//     if (name == "configreloaded") {
//         print(name)
//         Utils.execAsync(load_keybindings_cmd).then((out) => {
//             keybindings.setValue(JSON.parse(out));
//         });
//     }
// })

const icons = {
    super: ""
};

const replace = {
    slash: "/",
    period: ".",
    escape: "Esc"
};

const category_icons = {
    actions: "accessibility_new",
    applications: "apps",
    windows: "select_window",
    workspaces: "overview_key",
    misc: "construction",
    tools: "build"
};

const CheatSheet = () =>
    Widget.FlowBox({
        attribute: {
            set: (self) => {
                for (let category in keybindings.value) {
                    const box = Widget.Box({
                        class_name: "category",
                        vertical: true,
                        vpack: "fill",
                        children: [
                            Widget.Box({
                                children: [
                                    MaterialIcon(category_icons[category.toLowerCase()] || "category"),
                                    Widget.Label({
                                        label: category,
                                        class_name: "title",
                                        hpack: "start"
                                    })
                                ]
                            }),
                            Widget.Separator()
                        ]
                    });
                    let commands = keybindings.value[category];
                    for (const command in commands) {
                        const _command = command.replaceAll(" ", " + ");
                        const key_list = _command.split(" ");
                        const key_box = Widget.Box({
                            class_name: "row"
                        });
                        for (const key of key_list) {
                            if (key == "+")
                                key_box.pack_start(
                                    Widget.Label({
                                        label: "+",
                                        class_name: "plus",
                                        hpack: "start",
                                        vpack: "center"
                                    }),
                                    false,
                                    false,
                                    0
                                );
                            else if (icons[key])
                                key_box.pack_start(
                                    Widget.Label({
                                        label: icons[key],
                                        class_name: "awesome_icon key",
                                        hpack: "start",
                                        vpack: "center"
                                    }),
                                    false,
                                    false,
                                    0
                                );
                            else
                                key_box.pack_start(
                                    Widget.Label({
                                        label: replace[key.toLowerCase()] || key.charAt(0).toUpperCase() + key.slice(1),
                                        class_name: "key",
                                        hpack: "start",
                                        vpack: "center"
                                    }),
                                    false,
                                    false,
                                    0
                                );
                        }
                        key_box.pack_start(
                            Widget.Label({
                                label: `: `,
                                class_name: "separator",
                                hpack: "start",
                                vpack: "center"
                            }),
                            false,
                            false,
                            0
                        );
                        key_box.pack_start(
                            Widget.Label({
                                label: `${commands[command]}`,
                                class_name: "description",
                                hpack: "start",
                                vpack: "center"
                            }),
                            false,
                            false,
                            0
                        );
                        box.pack_start(key_box, false, false, 0);
                    }
                    self.add(box);
                }
            }
        },
        setup: (self) => {
            self.set_max_children_per_line(3);
            self.set_min_children_per_line(3);
            self.set_selection_mode(Gtk.SelectionMode.NONE);
            self.attribute.set(self);
        }
    });

export const cheatsheet = popupwindow({
    name: WINDOW_NAME,

    class_name: "cheatsheet",
    visible: false,
    keymode: "exclusive",
    child: CheatSheet(),
    anchor: []
});
