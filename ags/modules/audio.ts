import { Stream } from "types/service/audio";
import popupwindow from "./misc/popupwindow.ts";
import { MaterialIcon } from "icons.ts";
const audio = await Service.import("audio");
const WINDOW_NAME = "audio";

interface icons_type {
    [key: string]: [number, string][];
}

const icons: icons_type = {
    microphone: [
        [1, "mic"],
        [0, "mic_off"]
    ],
    headset_mic: [
        [1, "headset_mic"],
        [0, "headset_off"]
    ],
    speaker: [
        [101, "sound_detection_loud_sound"],
        [67, "volume_up"],
        [34, "volume_down"],
        [1, "volume_mute"],
        [0, "volume_off"]
    ]
};

const off_icons = {
    microphone: "mic_off",
    headset_mic: "headset_off",
    speaker: "volume_off"
};

const speaker = (stream: Stream, icons: [number, string][], off: string) => {
    const icon = Widget.Button({
        child: MaterialIcon(off, "20px").hook(stream, (self) => {
            const vol = stream.volume * 100;
            const icon = icons.find(([threshold]) => Number(threshold) <= vol)?.[1];
            if (stream.is_muted) self.label = off;
            else self.label = String(icon!);
            self.tooltip_text = `${Math.floor(stream.volume * 100)}%`;
        }),
        on_clicked: () => {
            stream.is_muted = !stream.is_muted;
        }
    });
    const slider = Widget.Slider({
        min: 0,
        max: 100,
        draw_value: false,
        hexpand: true,
        vpack: "end",
        value: stream.volume * 100,
        on_change: (self) => {
            stream.volume = self.value / 100;
            self.tooltip_text = `${Math.floor(stream.volume * 100)}%`;
        },
        setup: (self) => {
            self.hook(stream, () => {
                if (stream.volume > 1) {
                    if (self.max != 150) self.max = 150;
                } else {
                    if (self.max != 100) self.max = 100;
                }
                self.value = stream.volume * 100;
                self.tooltip_text = `${Math.floor(stream.volume * 100)}%`;
            });
        }
    });
    return Widget.Box({
        class_name: "device",
        vertical: true,
        attribute: { stream: stream },
        children: [
            Widget.Label({
                label: stream.description,
                hpack: "start",
                xalign: 0,
                truncate: "middle",
                tooltip_text: stream.name
            }),
            Widget.Box({
                children: [icon, slider]
            })
        ]
    });
};

export const audio_popup = popupwindow({
    name: WINDOW_NAME,

    class_name: "audio",
    visible: false,
    keymode: "exclusive",
    child: Widget.Scrollable({
        child: Widget.Box({
            vertical: true,
            children: [],
            setup: (self) => {
                function update() {
                    for (let s of audio.speakers) {
                        // @ts-expect-error
                        const existing = self.children.some((v) => v.attribute.stream.id == s.id);
                        if (!existing) self.pack_start(speaker(s, icons.speaker, off_icons.speaker), false, false, 0);
                    }
                    for (let s of audio.microphones) {
                        // @ts-expect-error
                        const existing = self.children.some((v) => v.attribute.stream.id == s.id);
                        let _icons = {
                            off: off_icons.microphone,
                            default: icons.microphone
                        };
                        if (s.icon_name == "audio-headset-analog-usb")
                            _icons = {
                                off: off_icons.headset_mic,
                                default: icons.headset_mic
                            };

                        if (!existing) self.pack_start(speaker(s, _icons.default, _icons.off), false, false, 0);
                    }
                }
                self.hook(App, (_, windowName, visible) => {
                    if (windowName !== WINDOW_NAME) return;

                    if (visible) update();
                });
                self.hook(audio, () => {
                    if (self.visible) update();
                });
            }
        }),
        hscroll: "never"
    }),
    anchor: ["top", "right", "bottom"]
});
