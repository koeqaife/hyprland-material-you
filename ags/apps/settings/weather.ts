import conf from "services/configuration.ts";

const WeatherKey = () =>
    Widget.EventBox({
        class_name: "row",
        on_secondary_click_release: (self) => {
            Utils.execAsync(`xdg-open "https://openweathermap.org/api"`).catch(print);
        },
        child: Widget.Box({
            class_name: "row",
            vpack: "start",
            children: [
                Widget.Box({
                    vertical: true,
                    hexpand: true,
                    vpack: "center",
                    hpack: "start",
                    children: [
                        Widget.Label({
                            hpack: "start",
                            class_name: "title",
                            label: "Api key"
                        }),
                        Widget.Label({
                            hpack: "start",
                            class_name: "description",
                            label: "openweathermap.org api key"
                        })
                    ]
                }),
                Widget.Entry({
                    max_length: 32,
                    hpack: "end",
                    css: "border: 2px solid; border-color: transparent;",
                    visibility: false,
                    text: conf.config.weather,
                    on_accept: (self) => {
                        if (self.text!.length == 32) {
                            self.css = "border: 2px solid; border-color: #66BB6A";
                            Utils.timeout(1000, () => {
                                self.css = "border: 2px solid; border-color: transparent";
                            });
                            conf.set_value("weather", self.text!);
                        }
                    }
                })
            ]
        })
    });

const WeatherLocationKey = () =>
    Widget.EventBox({
        class_name: "row",
        on_secondary_click_release: (self) => {
            Utils.execAsync(`xdg-open "https://openweathermap.org"`).catch(print);
        },
        child: Widget.Box({
            class_name: "row",
            vpack: "start",
            children: [
                Widget.Box({
                    vertical: true,
                    hexpand: true,
                    vpack: "center",
                    hpack: "start",
                    children: [
                        Widget.Label({
                            hpack: "start",
                            class_name: "title",
                            label: "Location key"
                        }),
                        Widget.Label({
                            hpack: "start",
                            class_name: "description",
                            label: "Search for your city at openweathermap.org"
                        })
                    ]
                }),
                Widget.Entry({
                    hpack: "end",
                    css: "border: 2px solid; border-color: transparent;",
                    text: conf.config.weather_location_id,
                    on_accept: (self) => {
                        self.css = "border: 2px solid; border-color: #66BB6A";
                        Utils.timeout(1000, () => {
                            self.css = "border: 2px solid; border-color: transparent";
                        });
                        conf.set_value("weather_location_id", self.text!);
                    }
                })
            ]
        })
    });

export function Weather() {
    const box = Widget.Box({
        vertical: true,
        children: [WeatherKey(), WeatherLocationKey()]
    });
    return Widget.Scrollable({
        hscroll: "never",
        child: box,
        vexpand: true
    });
}
