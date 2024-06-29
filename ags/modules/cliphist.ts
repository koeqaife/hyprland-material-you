const WINDOW_NAME = "cliphist"
import popupwindow from './misc/popupwindow.ts';
import Box from 'types/widgets/box.js';
const { Gtk } = imports.gi;


type EntryObject = {
    id: string;
    content: string;
    entry: string;
};


function ClipHistItem(entry: string) {
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
    let output: string;
    let entries: string[];
    let clipHistItems: EntryObject[];
    let widgets: Box<any, any>[];

    const list = Widget.Box({
        vertical: true,
        spacing,
    });

    async function repopulate() {
        output = await Utils.execAsync(`${App.configDir}/scripts/cliphist.sh --get`)
            .then(str => str)
            .catch(err => {
                print(err)
                return ""
            });
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
        class_name: "cliphistory_box",
        margin_top: 14,
        margin_right: 14,
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

