const apps_script = `python -OOO ${App.configDir}/scripts/apps.py`;

const Row = (app: string, title: string) => Widget.EventBox({
    class_name: "row",
    on_primary_click: self => {
        self.child.children[1]!.activate()
    },
    child: Widget.Box({
        class_name: "row",
        vpack: "start",
        children: [
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
                    "get": (self) => {
                        Utils.execAsync(`${apps_script} --get ${app}`)
                            .then((out) => {
                                self.text = out;
                            })
                            .catch(print)
                    }
                },
                on_accept: self => {
                    Utils.execAsync(`${apps_script} --${app} ${self.text}`)
                        .then(() => {
                            self.css = "border: 2px solid; border-color: #66BB6A;"
                            Utils.timeout(1000, () => {
                                self.css = "border: 2px solid; border-color: transparent"
                            })
                        })
                        .catch(() => {
                            self.css = "border: 2px solid; border-color: @error;"
                            Utils.timeout(1000, () => {
                                self.css = "border: 2px solid; border-color: transparent"
                            })
                            self.attribute.get(self)
                        })
                },
                setup: (self) => {
                    self.attribute.get(self)
                }
            })
        ]
    })
})


export function Apps() {
    const box = Widget.Box({
        vertical: true,
        children: [
            Row("browser", "Browser"),
            Row("editor", "Editor"),
            Row("filemanager", "File manager"),
            Row("terminal", "Terminal")
        ],
    })
    return Widget.Scrollable({
        hscroll: "never",
        child: box,
        vexpand: true
    })
}