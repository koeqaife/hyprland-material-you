
const { Gtk } = imports.gi;

function checkBrightness() {
    const get = Utils.execAsync(`${App.configDir}/scripts/brightness.sh --get`)
        .then(out => Number(out.trim()))
        .catch(print);
    return get
}

const current_brightness = Variable(100, {
    poll: [500, checkBrightness]
})

export function System() {
    return Widget.Slider({
        min: 0,
        max: 100,
        draw_value: false,
        // @ts-ignore
        value: current_brightness.bind(),
        on_change: self => {
            current_brightness.setValue(Number(self.value));
            Utils.execAsync(`${App.configDir}/scripts/brightness.sh --smooth ${self.value}`)
                .catch(print);
        }
    })
}
