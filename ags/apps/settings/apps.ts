const apps_script = `python -OOO ${App.configDir}/scripts/apps.py`;
import { MaterialIcon } from "icons";

const Row = (app: string, title: string, icon: string) =>
    Widget.EventBox({
        class_name: "row",
        on_primary_click_release: (self) => {
            self.child.children[1]!.activate();
        },
        child: Widget.Box({
            class_name: "row",
            vpack: "start",
            children: [
                MaterialIcon(icon),
                Widget.Box({
                    vertical: true,
                    hexpand: true,
                    vpack: "center",
                    children: [
                        Widget.Label({
                            hpack: "start",
                            class_name: "title",
                            label: title
                        })
                    ]
                }),
                Widget.Entry({
                    hpack: "end",
                    css: "border: 2px solid; border-color: transparent;",
                    attribute: {
                        get: (self) => {
                            Utils.execAsync(`${apps_script} --get ${app}`)
                                .then((out) => {
                                    self.text = out;
                                })
                                .catch(print);
                        }
                    },
                    on_accept: (self) => {
                        Utils.execAsync(`${apps_script} --${app} ${self.text}`)
                            .then(() => {
                                self.css = "border: 2px solid; border-color: #66BB6A;";
                                Utils.timeout(1000, () => {
                                    self.css = "border: 2px solid; border-color: transparent";
                                });
                            })
                            .catch(() => {
                                self.css = "border: 2px solid; border-color: @error;";
                                Utils.timeout(1000, () => {
                                    self.css = "border: 2px solid; border-color: transparent";
                                });
                                self.attribute.get(self);
                            });
                    },
                    setup: (self) => {
                        self.attribute.get(self);
                    }
                })
            ]
        })
    });

export function Apps() {
    const box = Widget.Box({
        vertical: true,
        children: [
            Row("browser", "Browser", "web"),
            Row("editor", "Editor", "edit"),
            Row("filemanager", "File manager", "folder"),
            Row("terminal", "Terminal", "terminal")
        ]
    });
    return Widget.Scrollable({
        hscroll: "never",
        child: box,
        vexpand: true
    });
}
