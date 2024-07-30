import { MaterialIcon } from "icons.ts";
import { type WeatherJson } from "variables";
import { Variable as VariableType } from "types/variable";
import configuration from "services/configuration.ts";
import { sideleft } from "./main";

// prettier-ignore
const MATERIAL_ICONS = {
    "50d": "mist", "50n": "mist",
    "01d": "clear_day", "01n": "bedtime",
    "02d": "partly_cloudy_day", "02n": "partly_cloudy_night",
    "03d": "cloud", "03n": "cloud",
    "04d": "cloud", "04n": "cloud",
    "09d": "rainy_heavy", "09n": "rainy_heavy",
    "10d": "rainy", "10n": "rainy",
    "11d": "thunderstorm", "11n": "thunderstorm",
    "13d": "weather_snowy", "13n": "weather_snowy",
    "40d": "air", "40n": "air"
};

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
};
const _reload = () => {
    if (sideleft?.visible) reload();
};
Utils.interval(15000, _reload);
configuration.connect("changed", _reload);
App.connect("window-toggled", (_, window_name, visible) => {
    if (window_name == "sideleft" && visible) reload();
});

const ICON_COLORS = {
    mist: "#B0BEC5",
    clear_day: "#FFEB3B",
    bedtime: "#9575CD",
    partly_cloudy_day: "#42A5F5",
    partly_cloudy_night: "#8C9EFF",
    cloud: "#81D4FA",
    rainy_heavy: "#039BE5",
    rainy: "#64B5F6",
    thunderstorm: "#FFB300",
    weather_snowy: "#4DD0E1",
    air: "#00ACC1"
};
const _T = "°";

function WeatherFirstCard(weather: WeatherJson) {
    const _box = (icon: string, info: string, tooltip?: string) =>
        Widget.Box({
            class_name: "info_box",
            children: [
                MaterialIcon(icon, "20px"),
                Widget.Label({
                    label: info
                })
            ],
            tooltip_text: tooltip
        });
    const temp_label = Widget.Label({
        class_name: "current",
        vpack: "end",
        label: `${Math.round(weather.main.temp)}${_T}`
    });
    const min_temp_label = Widget.Label({
        class_name: "min",
        vpack: "end",
        label: `${Math.round(weather.main.temp_min)}${_T}`
    });
    const max_temp_label = Widget.Label({
        class_name: "max",
        vpack: "end",
        label: `${Math.round(weather.main.temp_max)}${_T}`
    });
    const description = Widget.Label({
        class_name: "description",
        vpack: "center",
        hpack: "start",
        label: weather.weather[0].description.charAt(0).toUpperCase() + weather.weather[0].description.slice(1)
    });
    const real_feel = Widget.Label({
        class_name: "description",
        vpack: "center",
        hpack: "start",
        label: `RealFeel ${Math.round(weather.main.feels_like)}${_T}`
    });

    const _visibility = weather.visibility;
    let visibility: string;
    if (_visibility == 10000) visibility = "10km+";
    else if (_visibility >= 1000) visibility = `${(_visibility / 1000).toFixed(2)}km`;
    else visibility = `${Math.round(_visibility)}m`;

    const info = Widget.Box({
        spacing: 10,
        hexpand: true,
        children: [
            _box("visibility", visibility, "Visibility"),
            _box("cloud", `${weather.clouds.all}%`, "Cloudiness"),
            _box("humidity_percentage", `${weather.main.humidity}%`, "Humidity")
        ]
    });
    const color = ICON_COLORS[MATERIAL_ICONS[weather.weather[0].icon]];
    const temp = Widget.Box({
        class_name: "card",
        vpack: "start",
        hexpand: true,
        vertical: true,
        children: [
            Widget.Box({
                class_name: "temp",
                hpack: "start",
                children: [
                    MaterialIcon(MATERIAL_ICONS[weather.weather[0].icon], "", {
                        css: `font-size: 32px; color: ${color}`
                    }),
                    temp_label,
                    Widget.Separator({
                        vertical: true
                    }),
                    Widget.Box({
                        vertical: true,
                        children: [max_temp_label, min_temp_label]
                    })
                ]
            }),
            description,
            real_feel,
            info
        ]
    });
    return temp;
}

const _Label = (before: string, after: string) =>
    Widget.Box({
        children: [
            Widget.Label({
                class_name: "primary_label",
                label: before,
                hpack: "start"
            }),
            Widget.Label({
                class_name: "label",
                label: after,
                hpack: "start"
            })
        ]
    });

function WeatherSecondCard(weather: WeatherJson) {
    const wind = Widget.Box({
        class_name: "card",
        vpack: "start",
        hexpand: true,
        vertical: true,
        children: [
            Widget.Label({
                class_name: "title",
                label: "Wind",
                hpack: "start"
            }),
            _Label("Speed:", `${weather.wind.speed} m/s`),
            _Label("Gust:", `${weather.wind.gust} m/s`),
            _Label("Degrees:", `${weather.wind.deg}°`)
        ]
    });
    return wind;
}

export function WeatherBox() {
    return Widget.Box({
        class_name: "weather page",
        hexpand: true,
        vertical: true,
        setup: (self) => {
            self.hook(weather, () => {
                const cur_weather = weather.value;
                if (cur_weather["no_data"]) {
                    self.children = [
                        Widget.Box({
                            hpack: "center",
                            vpack: "center",
                            child: Widget.Label({
                                label: "Failed to retrieve information",
                                hpack: "center"
                            })
                        })
                    ];
                } else {
                    const title = Widget.Label({
                        class_name: "main_title",
                        label: cur_weather.name,
                        hpack: "start"
                    });
                    self.children = [title, WeatherFirstCard(cur_weather), WeatherSecondCard(cur_weather)];
                }
            });
        }
    });
}
