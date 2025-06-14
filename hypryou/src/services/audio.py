from repository import wp
from utils.ref import Ref
from utils.service import Service
import typing as t


ICON_THRESHOLDS: t.Final[tuple[float, ...]] = (
    0.0, 0.1,
    34.0, 67.0
)
ICON_VALUES: t.Final[tuple[str, ...]] = (
    "volume_off", "volume_mute",
    "volume_down", "volume_up"
)


def get_volume_icon(volume: float) -> str:
    for i in range(len(ICON_THRESHOLDS) - 1, -1, -1):
        if volume >= ICON_THRESHOLDS[i]:
            return ICON_VALUES[i]
    return ICON_VALUES[0]


volume = Ref(0.0, name="audio_volume")
volume_icon = Ref("volume_off", name="audio_volume_icon")
volume_icon.bind(volume, get_volume_icon)

streams = Ref[set[wp.Stream]](
    set(), name="audio_streams",
    types=(wp.Stream,)
)
recorders = Ref[set[wp.Stream]](
    set(), name="audio_recorders",
    types=(wp.Stream,)
)

speakers = Ref[set[wp.Endpoint]](
    set(), name="audio_speakers",
    types=(wp.Endpoint,)
)
microphones = Ref[set[wp.Endpoint]](
    set(), name="audio_mics",
    types=(wp.Endpoint,)
)


class AudioService(Service):
    def __init__(self) -> None:
        self.wp = wp.get_default()
        self.audio = self.wp.get_audio()
        self.default_speaker = self.audio.get_default_speaker()
        self.default_mic = self.audio.get_default_microphone()

    def on_volume_ref_changed(self, new_value: float) -> None:
        volume = self.default_speaker.get_volume() * 100.0
        if volume == new_value:
            return
        self.default_speaker.set_volume(new_value / 100.0)

    def on_volume_changed(self, *args: t.Any) -> None:
        volume.value = self.default_speaker.get_volume() * 100.0

    def app_init(self) -> None:
        volume.value = self.default_speaker.get_volume()
        volume.watch(self.on_volume_ref_changed)
        self.default_speaker.connect("notify::volume", self.on_volume_changed)

        targets: dict[str, Ref[set[wp.Stream]] | Ref[set[wp.Endpoint]]] = {
            "microphone": microphones,
            "stream": streams,
            "speaker": speakers,
            "recorder": recorders,
        }

        for node, container in targets.items():
            self.audio.connect(
                f"{node}-added",
                lambda _, n, c=container: c.value.add(n)
            )
            self.audio.connect(
                f"{node}-removed",
                lambda _, n, c=container: c.value.discard(n)
            )
