// by koeqaife ;)

const GLib = imports.gi.GLib;

export type WeatherJson = {
    coord: {
        lon: number;
        lat: number;
    };
    weather: [
        {
            id: number;
            main: string;
            description: string;
            icon: string;
        }
    ];
    base: string;
    main: {
        temp: number;
        feels_like: number;
        temp_min: number;
        temp_max: number;
        pressure: number;
        humidity: number;
        sea_level: number;
        grnd_level: number;
    };
    visibility: number;
    wind: {
        speed: number;
        deg: number;
        gust: number;
    };
    clouds: {
        all: number;
    };
    rain?: {
        "1h"?: string;
        "3h"?: string;
    };
    snow?: {
        "1h"?: string;
        "3h"?: string;
    };
    dt: number;
    sys: {
        type: number;
        id: number;
        country: string;
        sunrise: number;
        sunset: number;
    };
    timezone: number;
    id: number;
    name: string;
    cod: number;
    no_data?: boolean;
};

export type ThemeJson = {
    name: string;
    author: string;
    version: string;
    config_version: string;
    load_default_css: boolean;
    hide: boolean;
    description: string;
    path?: string;
};

export const theme = Variable("dark");
export const main_color = Variable("#000000");
export const current_wallpaper = Variable(`${GLib.get_home_dir()}/dotfiles/wallpapers/default.png`);

export const custom_theme = Variable<ThemeJson | null>(null);

export const idle_inhibitor = Variable(false);
export const cur_uptime = Variable("error");
Utils.interval(60000, () => {
    Utils.execAsync(`${App.configDir}/scripts/system.sh --uptime`)
        .then((out) => cur_uptime.setValue(out))
        .catch(print);
});
export const night_light = Variable(false);
Utils.execAsync(`${App.configDir}/scripts/night-light.sh --get`)
    .then((out) => {
        if (out.trim() == "enabled") night_light.setValue(true);
        else if (out.trim() == "disabled") night_light.setValue(false);
    })
    .catch(print);
export const theme_settings = {
    color: Variable("none"),
    scheme: Variable("tonalSpot")
};

const system_info = JSON.parse(await Utils.execAsync(`${App.configDir}/scripts/system.sh --json`));
export const cpu_name = system_info["cpu_name"]
export const gpu_name = system_info["gpu_name"]
export const cpu_cores = system_info["cpu_cores"];
export const amount_of_ram = system_info["ram"];
export const kernel_name = system_info["kernel"];
export const hostname = system_info["hostname"];
export const current_os = system_info["os"];

export const settings_file = `${GLib.get_home_dir()}/dotfiles/.settings/settings.json`;
export const wallpaper_cache_file = `${GLib.get_home_dir()}/.cache/current_wallpaper`;

function read_settings() {
    Utils.readFileAsync(settings_file)
        .then((out) => {
            const settings = JSON.parse(out);
            theme_settings.color.setValue(settings["custom-color"].trim());
            theme_settings.scheme.setValue(settings["generation-scheme"].trim());
            theme.setValue(settings["color-scheme"].trim());
        })
        .catch(print);

    Utils.readFileAsync(wallpaper_cache_file)
        .then((out) => {
            current_wallpaper.setValue(out.trim());
        })
        .catch((err) => {
            Utils.writeFileSync(current_wallpaper.value, wallpaper_cache_file);
        });
}
read_settings();

Utils.monitorFile(settings_file, read_settings);

Utils.monitorFile(wallpaper_cache_file, () => {
    Utils.readFileAsync(wallpaper_cache_file)
        .then((out) => {
            current_wallpaper.setValue(out);
        })
        .catch(print);
});
