const audio = await Service.import("audio");
import backlight_service from "services/backlight.ts";
import { MaterialIcon } from "icons.ts";
import Gtk from "types/@girs/gtk-3.0/gtk-3.0";
import Revealer from "types/widgets/revealer";
import Box from "types/widgets/box";
import Slider from "types/widgets/slider";
import { Binding } from "types/service";
import { audio_popup } from "./audio";

const brightness_icons = [
    "brightness_1",
    "brightness_2",
    "brightness_3",
    "brightness_4",
    "brightness_5",
    "brightness_6",
    "brightness_7"
];

function get_brightness_icon(brightness: number): string {
    const totalIcons = brightness_icons.length;
    const maxBrightness = 1;
    const ratio = 1.6;

    let thresholds: number[] = [];
    for (let i = 0; i < totalIcons; i++) {
        const threshold = maxBrightness / Math.pow(ratio, totalIcons - i - 1);
        thresholds.push(threshold);
    }

    for (let i = 0; i < totalIcons; i++) {
        if (brightness < thresholds[i]) {
            return brightness_icons[i];
        }
    }

    return brightness_icons[totalIcons - 1];
}

type popup_on_change = ((self: Slider<any>) => void) | undefined;
type popup_setup =
    | ((
          self: Revealer<
              Box<Gtk.Widget | Slider<unknown>, unknown>,
              {
                  count: number;
              }
          >
      ) => void)
    | undefined;

const default_popup = (
    icon: Gtk.Widget,
    value: number | Binding<any, any, number>,
    on_change?: popup_on_change,
    setup?: popup_setup
) =>
    Widget.Revealer({
        transition_duration: 200,
        transition: "slide_up",
        child: Widget.Revealer({
            reveal_child: false,
            transition_duration: 190,
            transition: "crossfade",
            child: Widget.Box({
                class_name: "popup",
                children: [
                    icon,
                    Widget.Slider({
                        min: 0,
                        max: 100,
                        draw_value: false,
                        class_name: "popup_slider",
                        value: value,
                        on_change: on_change
                    })
                ]
            }),
            attribute: { count: 0 },
            setup: setup
        }),
        setup: (self) => {
            self.child.connect("notify::child-revealed", () => {
                self.reveal_child = self.child.child_revealed;
            });
            self.child.connect("notify::reveal-child", () => {
                if (self.child.reveal_child) self.reveal_child = true;
            });
        }
    });

const backlight_popup = () =>
    default_popup(
        MaterialIcon("brightness_1").hook(backlight_service, (self) => {
            self.label = get_brightness_icon(backlight_service.screen_value);
        }),
        backlight_service.bind("screen_value").as((n) => n * 100),
        (self) => {
            backlight_service.screen_value = self.value / 100;
        },
        (self) => {
            backlight_service.connect("screen-changed", (_) => {
                self.attribute.count++;
                if (self.attribute.count > 0) self.reveal_child = true;
                Utils.timeout(1500, () => {
                    self.attribute.count--;
                    if (self.attribute.count <= 0) self.reveal_child = false;
                });
            });
        }
    );

const volume_popup = () =>
    default_popup(
        MaterialIcon("volume_off", "20px").hook(audio.speaker, (self) => {
            const vol = audio.speaker.volume * 100;
            const icon = [
                [101, "sound_detection_loud_sound"],
                [67, "volume_up"],
                [34, "volume_down"],
                [1, "volume_mute"],
                [0, "volume_off"]
            ].find(([threshold]) => Number(threshold) <= vol)?.[1];
            if (audio.speaker.is_muted) self.label = "volume_off";
            else self.label = String(icon!);
        }),
        audio.speaker.bind("volume").as((volume) => Math.floor(volume * 100)),
        (self) => {
            audio.speaker.volume = self.value / 100;
        },
        (self) => {
            audio.speaker.connect("notify::volume", (_) => {
                if (audio_popup.visible) return;
                self.attribute.count++;
                if (self.attribute.count > 0) self.reveal_child = true;
                Utils.timeout(1500, () => {
                    self.attribute.count--;
                    if (self.attribute.count <= 0) self.reveal_child = false;
                });
            });
        }
    );

export const popups = (monitor = 0) => {
    const _volume_popup = volume_popup();
    const _backlight_popup = backlight_popup();
    return Widget.Window({
        monitor,
        name: `popups${monitor}`,
        child: Widget.Box({
            css: "min-height: 1px; min-width: 1px;",
            vertical: true,
            children: [_backlight_popup, _volume_popup]
        }),
        class_name: "popups",
        anchor: ["top"],
        visible: true
    });
};
