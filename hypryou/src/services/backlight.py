
from src.services.login1 import get_login_manager
from utils.service import Service, Signals
from utils import Ref
from repository import gio
import typing as t
from utils.logger import logger
import os

NAMESPACE_DIR = "/sys/class/backlight"


class BacklightDevice(Signals):
    def __init__(self, device: str) -> None:
        super().__init__()
        self.device = device
        self.directory = f"{NAMESPACE_DIR}/{device}"
        self.brightness_file_path = f"{self.directory}/brightness"
        self.max_brightness_file_path = f"{self.directory}/max_brightness"
        self.icon = Ref(
            "brightness_7",
            name=f"{device}.icon"
        )

        self.brightness_file = gio.File.new_for_path(self.brightness_file_path)
        self.max_brightness_file = gio.File.new_for_path(
            self.max_brightness_file_path
        )

        self.monitor = self.brightness_file.monitor_file(
            gio.FileMonitorFlags.NONE, None
        )
        self.brightness = 0
        self.brightness_file.read_async(
            0, None, self.brightness_finish, None
        )

        self.max_brightness = -1
        self.changed_threshold = 0
        self.update_max_brightness()

        self.monitor_handler = self.monitor.connect(
            "changed", self.on_changed
        )

    def update_icon(self) -> None:
        normalized = self.brightness / self.max_brightness
        level = round((normalized ** 0.5) * 7)
        level = max(level, 1)
        self.icon.value = f"brightness_{level}"

    def set_brightness(
        self,
        value: int,
        notify_external: bool = False
    ) -> None:
        self.brightness = value
        self.notify("changed", value)
        if notify_external:
            self.notify("changed-external", value)
        get_login_manager().set_brightness(
            "backlight",
            self.device,
            value
        )
        self.update_icon()

    def update_max_brightness(self) -> None:
        try:
            stream = self.max_brightness_file.read(None)
            bytes = stream.read_bytes(1024, None)
            data = bytes.get_data()
            if data is None:
                raise TypeError("Max_brightness file content is None")
            else:
                value = int(data.decode("utf-8").strip())
                self.max_brightness = value
                self.changed_threshold = self.max_brightness * 0.005
        except Exception as e:
            logger.error(
                "Couldn't read max_brightness file.",
                exc_info=e
            )

    def destroy(self) -> None:
        self.monitor.disconnect(self.monitor_handler)
        self.monitor.cancel()

    def brightness_finish(
        self,
        file: gio.File,
        result: gio.AsyncResult,
        user_data: t.Any
    ) -> None:
        try:
            stream = file.read_finish(result)
            bytes = stream.read_bytes(1024, None)
            data = bytes.get_data()
            if data is None:
                raise TypeError("Brightness file content is None")
            else:
                value = int(data.decode("utf-8").strip())
                if value == self.brightness:
                    pass
                elif abs(value - self.brightness) > self.changed_threshold:
                    self.brightness = value
                    self.notify("changed", value)
                    self.notify("changed-external", value)
                    self.update_icon()
        except Exception as e:
            logger.error(
                "Couldn't read brightness file.",
                exc_info=e
            )

    def on_changed(
        self,
        _: gio.FileMonitor,
        file: gio.File,
        user_data: t.Any,
        event: gio.FileMonitorEvent
    ) -> None:
        if event != gio.FileMonitorEvent.CHANGES_DONE_HINT:
            return
        self.brightness_file.read_async(
            0, None, self.brightness_finish, None
        )


class BacklightManager:
    def __init__(self) -> None:
        self.login1 = get_login_manager()
        self.devices: list[BacklightDevice] = []
        self.scan()

    def scan(self) -> None:
        base_path = NAMESPACE_DIR
        candidates = []
        for entry in os.listdir(base_path):
            full_path = os.path.join(base_path, entry)
            if os.path.isfile(os.path.join(full_path, "brightness")):
                with open(os.path.join(full_path, "max_brightness")) as f:
                    try:
                        max_val = int(f.read().strip())
                    except ValueError:
                        continue
                candidates.append((entry, max_val))

        preferred_order = ["intel", "amdgpu", "nvidia", "acpi"]
        candidates.sort(key=lambda x: (
            next((i for i, p in enumerate(preferred_order) if p in x[0]), 99),
            -x[1]
        ))
        self.devices = [
            BacklightDevice(device)
            for device, max_brightness
            in candidates
            if max_brightness > 99
        ]


_instance: BacklightManager | None = None


def get_backlight_manager() -> BacklightManager:
    if not _instance:
        raise RuntimeError(
            "Couldn't get instance of backlight manager. " +
            "Most likely it's not initialized."
        )

    return _instance


class BacklightService(Service):
    def app_init(self) -> None:
        global _instance
        _instance = BacklightManager()
