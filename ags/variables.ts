const GLib = imports.gi.GLib;

export const theme = Variable("dark");
export const main_color = Variable("#000000");

export const idle_inhibitor = Variable(false);
export const night_light = Variable(false);
export const bluetooth_enabled = Variable('off', {
    poll: [1000, `${App.configDir}/scripts/bluetooth.sh --get`]
})


const color_scheme_file = `${GLib.get_home_dir()}/dotfiles/.settings/color-scheme`
Utils.readFileAsync(color_scheme_file)
    .then(out => { theme.setValue(out); })
    .catch(err => { });


Utils.monitorFile(
    color_scheme_file,
    () => {
        Utils.readFileAsync(color_scheme_file)
            .then(out => { theme.setValue(out); })
            .catch(err => { });
    }
)