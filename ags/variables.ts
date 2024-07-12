import { Variable as VariableType } from "types/variable";
const GLib = imports.gi.GLib;
import configuration from "services/configuration.ts";

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

export const theme = Variable("dark");
export const main_color = Variable("#000000");
export const current_wallpaper = Variable(`${GLib.get_home_dir()}/dotfiles/wallpapers/default.png`);
// @ts-expect-error
export const weather: VariableType<WeatherJson> = Variable({ no_data: true });
const reload = () => {
    if (configuration.config.weather != "" && configuration.config.weather_location_id != "")
        Utils.execAsync(
            `${App.configDir}/scripts/weather.sh weather ${configuration.config.weather} ${configuration.config.weather_location_id}`
        )
            .then((out) => {
                weather.setValue(JSON.parse(out));
            })
            .catch(print);
}
Utils.interval(15000, reload);
configuration.connect("changed", reload)

export const idle_inhibitor = Variable(false);
export const cur_uptime = Variable("error");
Utils.interval(5000, () => {
    Utils.execAsync(`${App.configDir}/scripts/system.sh --uptime`)
        .then((out) => cur_uptime.setValue(out))
        .catch(print);
});
export const night_light = Variable(false);
export const bluetooth_enabled = Variable("off", {
    poll: [1000, `${App.configDir}/scripts/bluetooth.sh --get`]
});
export const theme_settings = {
    color: Variable("none"),
    scheme: Variable("tonalSpot")
};

export const cpu_name = await Utils.execAsync(`${App.configDir}/scripts/system.sh --cpu-name`);
export const gpu_name = await Utils.execAsync(`${App.configDir}/scripts/system.sh --gpu-name`);
export const cpu_cores = await Utils.execAsync(`${App.configDir}/scripts/system.sh --cpu-cores`);
export const amount_of_ram = await Utils.execAsync(`${App.configDir}/scripts/system.sh --ram`);
export const kernel_name = await Utils.execAsync(`${App.configDir}/scripts/system.sh --kernel`);
export const hostname = await Utils.execAsync(`${App.configDir}/scripts/system.sh --hostname`);
export const current_os = await Utils.execAsync(`${App.configDir}/scripts/system.sh --os`);

export const custom_color_file = `${GLib.get_home_dir()}/dotfiles/.settings/custom-color`;
export const generation_scheme_file = `${GLib.get_home_dir()}/dotfiles/.settings/generation-scheme`;
export const color_scheme_file = `${GLib.get_home_dir()}/dotfiles/.settings/color-scheme`;
export const wallpaper_cache_file = `${GLib.get_home_dir()}/.cache/current_wallpaper`;

function readFiles() {
    Utils.readFileAsync(custom_color_file)
        .then((out) => {
            let _out = out;
            if (_out.startsWith("-")) {
                _out = _out.substring(1);
            }
            theme_settings.color.setValue(_out.trim());
        })
        .catch(print);

    Utils.readFileAsync(generation_scheme_file)
        .then((out) => {
            theme_settings.scheme.setValue(out);
        })
        .catch(print);

    Utils.readFileAsync(color_scheme_file)
        .then((out) => {
            theme.setValue(out.trim());
        })
        .catch((err) => {});

    Utils.readFileAsync(wallpaper_cache_file)
        .then((out) => {
            current_wallpaper.setValue(out.trim());
        })
        .catch((err) => {
            Utils.writeFileSync(current_wallpaper.value, wallpaper_cache_file);
        });
}
readFiles();

Utils.monitorFile(custom_color_file, () => {
    Utils.readFileAsync(custom_color_file)
        .then((out) => {
            let _out = out;
            if (_out.startsWith("-")) {
                _out = _out.substring(1);
            }
            theme_settings.color.setValue(_out.trim());
        })
        .catch((err) => {});
});

Utils.monitorFile(generation_scheme_file, () => {
    Utils.readFileAsync(generation_scheme_file)
        .then((out) => {
            theme_settings.scheme.setValue(out.trim());
        })
        .catch((err) => {});
});

Utils.monitorFile(color_scheme_file, () => {
    Utils.readFileAsync(color_scheme_file)
        .then((out) => {
            theme.setValue(out.trim());
        })
        .catch((err) => {});
});

Utils.monitorFile(wallpaper_cache_file, () => {
    Utils.readFileAsync(wallpaper_cache_file)
        .then((out) => {
            current_wallpaper.setValue(out);
        })
        .catch(print);
});
