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
const IconButton = (
    icon: string,
    size: string,
    stream: Stream,
    on_clicked: () => void,
    icons: [number, string][],
    off: string
) =>
    Widget.Button({
        child: MaterialIcon(icon, size).hook(stream, (self) => {
            const vol = stream.volume * 100;
            const icon = icons.find(([threshold]) => Number(threshold) <= vol)?.[1];
            if (stream.is_muted) self.label = off;
            else self.label = String(icon!);
            self.tooltip_text = `${Math.floor(stream.volume * 100)}%`;
        }),
        on_clicked: on_clicked
    });

const Slider = (stream: Stream) =>
    Widget.Slider({
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
                self.max = stream.volume > 1 ? 150 : 100;
                self.value = stream.volume * 100;
                self.tooltip_text = `${Math.floor(stream.volume * 100)}%`;
            });
        }
    });

const Speaker = (stream: Stream, icons: [number, string][], off: string) =>
    Widget.Box({
        class_name: "device",
        vertical: true,
        attribute: { stream: stream },
        children: [
            Widget.Box({
                children: [
                    Widget.Label({
                        label: stream.description,
                        xalign: 0,
                        truncate: "end",
                        hexpand: true,
                        tooltip_text: stream.name,
                        css: "margin-right: 4px;"
                    }),
                    Widget.Label({
                        label: stream.bind("volume").as((v) => `${Math.round(v * 100)}%`),
                        xalign: 1
                    })
                ]
            }),
            Widget.Box({
                children: [
                    IconButton(
                        off,
                        "20px",
                        stream,
                        () => {
                            stream.is_muted = !stream.is_muted;
                        },
                        icons,
                        off
                    ),
                    Slider(stream)
                ]
            })
        ]
    });

const app = (stream: Stream) => {
    const label = !!stream.name ? `${stream.name}: ${stream.description}` : stream.description;
    return Widget.Box({
        class_name: "device",
        vertical: true,
        attribute: { stream: stream },
        children: [
            Widget.Box({
                children: [
                    Widget.Label({
                        label: label,
                        xalign: 0,
                        truncate: "end",
                        hexpand: true,
                        tooltip_text: label,
                        css: "margin-right: 4px;"
                    }),
                    Widget.Label({
                        label: stream.bind("volume").as((v) => `${Math.round(v * 100)}%`),
                        xalign: 1
                    })
                ]
            }),

            Widget.Box({
                children: [
                    Widget.Button({
                        child: Widget.Icon({ icon: stream.icon_name || "image-missing", size: 20 }),
                        on_clicked: () => {
                            stream.is_muted = !stream.is_muted;
                        }
                    }),
                    Slider(stream)
                ]
            })
        ]
    });
};

const Tab = (icon: string, on_clicked: (any) => void, page?: string) =>
    Widget.Overlay({
        child: Widget.Button({
            hexpand: true,
            vexpand: true,
            on_clicked: on_clicked
        }),
        pass_through: true,
        attribute: { page: page || icon },
        overlays: [MaterialIcon(icon, "22px")]
    });

const Audio = () => {
    const cur_page = Variable("speakers");
    const tabs = Widget.Box({
        class_name: "tabs",
        children: [
            Tab("volume_up", () => cur_page.setValue("speakers"), "speakers"),
            Tab("apps", () => cur_page.setValue("apps"), "apps")
        ],
        setup: (self) => {
            self.hook(cur_page, () => {
                self.children.forEach((widget) => {
                    widget.toggleClassName("active", widget.attribute.page == cur_page.value);
                });
            });
        }
    });
    const speakers = Widget.Box({ vertical: true, children: [] as ReturnType<typeof Speaker>[] });
    const apps = Widget.Box({ vertical: true, children: [] as ReturnType<typeof app>[] });

    function update() {
        const speaker_ids = audio.speakers.map((s) => s.id);
        const app_ids = audio.apps.map((s) => s.id);
        const microphone_ids = audio.microphones.map((s) => s.id);

        speakers.children
            .filter(
                (widget) =>
                    !speaker_ids.includes(widget.attribute.stream.id) &&
                    !microphone_ids.includes(widget.attribute.stream.id)
            )
            .forEach((widget) => widget.destroy());

        apps.children
            .filter((widget) => !app_ids.includes(widget.attribute.stream.id))
            .forEach((widget) => widget.destroy());

        audio.speakers.forEach((s) => {
            if (!speakers.children.some((v) => v.attribute.stream.id == s.id)) {
                speakers.pack_start(Speaker(s, icons.speaker, off_icons.speaker), false, false, 0);
            }
        });

        audio.microphones.forEach((s) => {
            if (!speakers.children.some((v) => v.attribute.stream.id == s.id)) {
                const _icons =
                    s.icon_name == "audio-headset-analog-usb"
                        ? { off: off_icons.headset_mic, default: icons.headset_mic }
                        : { off: off_icons.microphone, default: icons.microphone };
                speakers.pack_start(Speaker(s, _icons.default, _icons.off), false, false, 0);
            }
        });

        audio.apps.forEach((s) => {
            if (!apps.children.some((v) => v.attribute.stream.id == s.id)) {
                apps.pack_start(app(s), false, false, 0);
            }
        });
    }

    update();
    ["notify::speakers", "notify::apps", "notify::microphones"].forEach((event) => {
        audio.connect(event, () => {
            if (audio_popup.visible) update();
        });
    });

    const stack = Widget.Stack({
        children: { speakers, apps },
        // @ts-expect-error
        shown: cur_page.bind(),
        transition: "crossfade"
    });

    return Widget.Scrollable({
        child: Widget.Box({
            class_name: "audio_box",
            vpack: "start",
            vertical: true,
            children: [tabs, stack]
        }),
        hscroll: "never",
        setup: (self) => {
            self.hook(App, (_, windowName, visible) => {
                if (windowName !== WINDOW_NAME) return;
                if (visible) update();
            });
        }
    });
};

export const audio_popup = popupwindow({
    name: WINDOW_NAME,
    class_name: "audio",
    visible: false,
    keymode: "exclusive",
    child: Audio(),
    anchor: ["top", "right", "bottom"]
});
