const { Gtk } = imports.gi;

function checkBacklight() {
    const get = Utils.execAsync(`${App.configDir}/scripts/backlight.sh --get`)
        .then(out => Number(out.trim()))
        .catch(print);
    return get
}

function checkBrightness() {
    const get = Utils.execAsync(`${App.configDir}/scripts/brightness.sh --get`)
        .then(out => Number(out.trim()))
        .catch(print);
    return get
}

const current_backlight = Variable(100, {
    poll: [500, checkBacklight]
})

const current_brightness = Variable(100, {
    poll: [500, checkBrightness]
})

const Label = (label: string) => Widget.Label({
        label: label,
        hpack: "start",
        class_name: "bold_label"
    })

export function SystemBox() {
    const backlight = Widget.Slider({
        min: 0,
        max: 100,
        draw_value: false,
        class_name: "system_scale",
        // @ts-ignore
        value: current_backlight.bind(),
        on_change: self => {
            current_backlight.setValue(Number(self.value));
            Utils.execAsync(`${App.configDir}/scripts/backlight.sh --smooth ${self.value}`)
                .catch(print);
        }
    })
    const brightness = Widget.Slider({
        min: 0,
        max: 1,
        draw_value: false,
        class_name: "system_scale",
        // @ts-ignore
        value: current_brightness.bind(),
        on_change: self => {
            current_brightness.setValue(Number(self.value));
            Utils.execAsync(`${App.configDir}/scripts/brightness.sh --set ${self.value}`)
                .catch(print);
        }
    })
    return Widget.Box({
        orientation: Gtk.Orientation.VERTICAL,
        class_name: "system_box",
        spacing: 14,
        children: [
            Label("Backlight:"),
            backlight,
            Label("Brightness:"),
            brightness
        ]
    })
}
