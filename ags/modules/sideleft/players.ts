import { MprisPlayer } from "types/service/mpris.ts";
import Label from "types/widgets/label.ts";
import { MaterialIcon } from "icons.ts";
import Pango10 from "gi://Pango?version=1.0";
const mpris = await Service.import("mpris");
const players = mpris.bind("players");

const FALLBACK_ICON = "audio-x-generic-symbolic";
const PLAY_ICON = "play_arrow";
const PAUSE_ICON = "pause";
const PREV_ICON = "skip_previous";
const NEXT_ICON = "skip_next";

function length_str(length: number): string {
    const min = Math.floor(length / 60);
    const sec = Math.floor(length % 60);
    const sec0 = sec < 10 ? "0" : "";
    return `${min}:${sec0}${sec}`;
}

function Player(player: MprisPlayer) {
    const img = Widget.Box({
        class_name: "img",
        vpack: "start",
        css: player.bind("cover_path").transform(
            (p) => `
            background-image: url('${p}');
        `
        )
    });

    const title = Widget.Label({
        class_name: "title",
        wrap: true,
        wrap_mode: Pango10.WrapMode.WORD_CHAR,
        xalign: 0,
        label: player.bind("track_title"),
        use_markup: false
    });

    const artist = Widget.Label({
        class_name: "artist",
        wrap: true,
        wrap_mode: Pango10.WrapMode.WORD_CHAR,
        xalign: 0,
        use_markup: false,
        label: player.bind("track_artists").transform((a) => a.join(", "))
    });

    const positionSlider = Widget.Slider({
        class_name: "position",
        draw_value: false,
        on_change: ({ value }) => (player.position = value * player.length),
        visible: player.bind("length").as((l) => l > 0),
        setup: (self) => {
            function update() {
                const value = player.position / player.length;
                self.value = value > 0 ? value : 0;
            }
            self.hook(player, update);
            self.hook(player, update, "position");
            self.poll(1000, update);
        }
    });

    const positionLabel = Widget.Label({
        class_name: "position",
        hpack: "start",
        setup: (self) => {
            const update = (self: Label<any>) => {
                self.label = length_str(player.position);
                self.visible = player.length > 0;
            };

            self.hook(player, update, "position");
            self.poll(1000, update);
        }
    });

    const lengthLabel = Widget.Label({
        class_name: "length",
        hpack: "end",
        visible: player.bind("length").transform((l) => l > 0),
        label: player.bind("length").transform(length_str)
    });

    const icon = Widget.Icon({
        class_name: "icon",
        hexpand: true,
        hpack: "end",
        vpack: "start",
        tooltip_text: player.identity || "",
        icon: player.bind("entry").transform((entry) => {
            const name = `${entry}-symbolic`;
            return Utils.lookUpIcon(name) ? name : FALLBACK_ICON;
        })
    });

    const playPause = Widget.Button({
        class_name: "play-pause",
        on_clicked: () => player.playPause(),
        visible: player.bind("can_play"),
        child: MaterialIcon(
            // @ts-expect-error
            player.bind("play_back_status").transform((s) => {
                switch (s) {
                    case "Playing":
                        return PAUSE_ICON;
                    case "Paused":
                    case "Stopped":
                        return PLAY_ICON;
                }
            }),
            "18px"
        )
    });

    const prev = Widget.Button({
        on_clicked: () => player.previous(),
        visible: player.bind("can_go_prev"),
        child: MaterialIcon(PREV_ICON, "18px")
    });

    const next = Widget.Button({
        on_clicked: () => player.next(),
        visible: player.bind("can_go_next"),
        child: MaterialIcon(NEXT_ICON, "18px")
    });

    return Widget.Box(
        {
            class_name: "card player",
            vpack: "start"
        },
        img,
        Widget.Box(
            {
                vertical: true,
                hexpand: true
            },
            Widget.Box([title, icon]),
            artist,
            Widget.Box({ vexpand: true }),
            positionSlider,
            Widget.CenterBox({
                start_widget: positionLabel,
                center_widget: Widget.Box({
                    class_name: "player_buttons",
                    children: [prev, playPause, next]
                }),
                end_widget: lengthLabel
            })
        )
    );
}

export function Media() {
    return Widget.Box({
        vertical: true,
        css: "min-height: 2px; min-width: 2px;",
        vpack: "start",
        visible: players.as((p) => p.length > 0),
        children: players.as((p) => p.map(Player))
    });
}
