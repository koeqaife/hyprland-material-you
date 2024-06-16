const { GLib } = imports.gi;
const WINDOW_NAME = "cliphist"
import popupwindow from './.widgethacks/popupwindow.js';
const { Gtk } = imports.gi;


function ClipHistItem(entry) {
    let [id, ...content] = entry.split('\t');
    let clickCount = 0;
    let button = Widget.Button({
        class_name: "entry_container",
        child: Widget.Label({
            label: entry,
            class_name: "entry_label",
            xalign: 0,
            vpack: "center",
            truncate: "end",
        })
    })

    button.connect('clicked', () => {
        clickCount++;
        if (clickCount === 2) {
            App.closeWindow(WINDOW_NAME);
            Utils.execAsync(`${App.configDir}/scripts/cliphist.sh --copy-by-id ${id}`)
            clickCount = 0;
        }
    });

    button.connect('focus-out-event', () => {
        clickCount = 0;
    });

    return Widget.Box({
        attribute: { content: content.join(' ').trim() },
        orientation: Gtk.Orientation.VERTICAL,
        children: [
            button,
            Widget.Separator({
                class_name: "entry_divider",
                orientation: Gtk.Orientation.HORIZONTAL
            })
        ]
    })
}


function ClipHistWidget({ width = 500, height = 500, spacing = 12 }) {
    let output;
    let entries;
    let clipHistItems;
    let widgets;

    const list = Widget.Box({
        vertical: true,
        spacing,
    });

    function repopulate() {
        output = Utils.exec(`${App.configDir}/scripts/cliphist.sh --get`);
        entries = output.split('\n').filter(line => line.trim() !== '');
        clipHistItems = entries.map(entry => {
            let [id, ...content] = entry.split('\t');
            return { id: id.trim(), content: content.join(' ').trim(), entry: entry };
        });
        widgets = clipHistItems.map(item => ClipHistItem(item.entry));
        list.children = widgets;
    }
    repopulate();

    const entry = Widget.Entry({
        hexpand: true,
        class_name: "cliphistory_entry",
        placeholder_text: "Search",

        on_change: ({ text }) => widgets.forEach(item => {
            item.visible = item.attribute.content.match(text ?? "")
        }),
    })

    return Widget.Box({
        vertical: true,
        css: `margin: ${spacing * 2}px;`,
        class_name: "cliphistory_box",
        margin_top: 15,
        margin_left: 15,
        children: [
            entry,
            Widget.Scrollable({
                hscroll: "never",
                css: `min-width: ${width}px;`
                    + `min-height: ${height}px;`,
                child: list,
            }),
        ],
        setup: self => self.hook(App, (_, windowName, visible) => {
            if (windowName !== WINDOW_NAME)
                return

            if (visible) {
                repopulate()
                entry.text = ""
            }
        }),
    })
}


export const cliphist = popupwindow({
    name: WINDOW_NAME,

    class_name: "cliphistory",
    visible: false,
    keymode: "exclusive",
    child: ClipHistWidget({
        width: 500,
        height: 500,
        spacing: 0,
    }),
    anchor: ["top", "right"]
})

