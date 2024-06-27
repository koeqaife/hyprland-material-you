const GLib = imports.gi.GLib;

export const theme = Variable("dark");
export const main_color = Variable("#000000");
export const current_wallpaper = Variable(`${GLib.get_home_dir()}/dotfiles/wallpapers/default.png`);

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
const wallpaper_cache_file = `${GLib.get_home_dir()}/.cache/current_wallpaper`
Utils.readFileAsync(wallpaper_cache_file)
    .then(out => { current_wallpaper.setValue(out.trim()); })
    .catch(err => {
        Utils.writeFileSync(current_wallpaper.value, wallpaper_cache_file)
    });

Utils.monitorFile(
    wallpaper_cache_file,
    () => {
        Utils.readFileAsync(wallpaper_cache_file)
            .then(out => { current_wallpaper.setValue(out); })
            .catch(print);
    }
)
