import asyncio
from enum import Enum
import os
from asyncio import StreamReader, StreamWriter
from utils.ref import Ref
from utils.logger import logger
import typing as t
import json
from config import HyprlandVars
from utils.service import Signals, AsyncService

active_workspace = Ref(0, name="workspace", delayed_init=True)
active_layout = Ref("en", name="active_layout", delayed_init=True)
show_layout = Ref(False, name="show_layout", delayed_init=True)
night_light = Ref(False, name="night_light", delayed_init=True)

workspace_ids = Ref[set[int]](
    set(),
    name="workspace_ids",
    delayed_init=True
)
initialized = Ref(False)


HyprlandQueryType = t.Literal[
    "activewindow",
    "activeworkspace",
    "clients",
    "devices",
    "dispatch",
    "getoption",
    "hyprlandversion",
    "junct",
    "layers",
    "monitors",
    "splash",
    "workspaces"
]


class SocketType(int, Enum):
    HYPRLAND = 0
    HYPRSUNSET = 1


class HyprlandClient(Signals):
    def __init__(self) -> None:
        super().__init__()
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000")
        instance = os.environ["HYPRLAND_INSTANCE_SIGNATURE"]

        instance_path = f"{runtime_dir}/hypr/{instance}"
        self.socket_path_events = f"{instance_path}/.socket2.sock"
        self.sockets = {
            SocketType.HYPRLAND: f"{instance_path}/.socket.sock",
            SocketType.HYPRSUNSET: f"{instance_path}/.hyprsunset.sock"
        }

        self.reader: StreamReader | None = None
        self.writer: StreamWriter | None = None

    async def connect(self) -> None:
        self.reader, self.writer = await asyncio.open_unix_connection(
            self.socket_path_events
        )
        while True:
            line = await self.reader.readline()
            if not line:
                break
            decoded = line.decode().rstrip("\n")
            if ">>" not in decoded:
                continue
            event, data = decoded.split(">>", 1)
            args: list[str] = data.split(",") if data else []
            self.notify(event, *args)

    async def raw(
        self,
        command: str,
        socket_type: SocketType = SocketType.HYPRLAND,
        timeout: float = 2.0,
        wait_response: bool = True
    ) -> str:
        reader, writer = await asyncio.open_unix_connection(
            self.sockets[socket_type]
        )
        writer.write(command.encode("utf-8"))
        await writer.drain()
        data = b""
        if wait_response:
            try:
                data = await asyncio.wait_for(
                    reader.read(4096),
                    timeout=timeout
                )
            except asyncio.TimeoutError as e:
                writer.close()
                await writer.wait_closed()
                logger.error(
                    f"Timeout waiting for response to command: {command!r}",
                    exc_info=e
                )
                return ""
        else:
            try:
                await asyncio.wait_for(reader.read(1), timeout=timeout)
            except asyncio.TimeoutError:
                pass

        writer.close()
        await writer.wait_closed()
        return data.decode().strip()

    async def query(self, command: HyprlandQueryType | str) -> t.Any:
        raw_result = await self.raw(f"j/{command}")
        try:
            return json.loads(raw_result)
        except json.JSONDecodeError:
            return raw_result

    async def dispatch(self, subcommand: str) -> str:
        return await self.raw(f"dispatch {subcommand}")


client: HyprlandClient


class EventCallbacks:
    @staticmethod
    def on_workspacev2(
        new_workspace_id: str,
        new_workspace_name: str
    ) -> None:
        active_workspace.value = int(new_workspace_id)

    @staticmethod
    def on_focusedmonv2(
        new_monitor_name: str,
        new_workspace_id: str
    ) -> None:
        active_workspace.value = int(new_workspace_id)

    @staticmethod
    def on_activelayout(
        keyboard_name: str,
        layout_name: str
    ) -> None:
        if layout_name != active_layout.value:
            show_layout.value = True
        active_layout.value = layout_name

    @staticmethod
    def on_createworkspacev2(
        workspace_id: str,
        workspace_name: str
    ) -> None:
        if int(workspace_id) not in workspace_ids.value:
            workspace_ids.value.add(int(workspace_id))

    @staticmethod
    def on_destroyworkspacev2(
        workspace_id: str,
        workspace_name: str
    ) -> None:
        if int(workspace_id) in workspace_ids.value:
            workspace_ids.value.remove(int(workspace_id))


class Keyboard(t.TypedDict):
    address: str
    name: str
    rules: str
    model: str
    layout: str
    variant: str
    options: str
    active_keymap: str
    capsLock: bool
    numLock: bool
    main: bool


def get_layouts(keyboard: Keyboard) -> list[str]:
    return keyboard["layout"].strip().strip(",").split(",")


async def get_active_layout(client: HyprlandClient) -> tuple[bool, str]:
    show_layout = False
    devices = await client.query("devices")
    keyboards: list[Keyboard] = devices.get("keyboards")
    assert isinstance(keyboards, list), (
        "Keyboards type isn't correct! " +
        f"{type(keyboards)} != list"
    )

    if not keyboards:
        return "English (US)"

    for keyboard in keyboards:
        if keyboard["main"]:
            show_layout = len(get_layouts(keyboard)) > 1
            return show_layout, keyboard["active_keymap"]

    keyboard = keyboards[-1]
    show_layout = len(get_layouts(keyboard)) > 1
    return show_layout, keyboard["active_keymap"]


async def get_active_workspaces(client: HyprlandClient) -> list[int]:
    workspaces = await client.query("workspaces")
    assert isinstance(workspaces, list), (
        "Workspaces has to be list. " +
        f"{type(workspaces)} != list"
    )

    workspace_ids = [int(object["id"]) for object in workspaces]
    return workspace_ids


def change_night_light(value: bool) -> None:
    if value:
        asyncio.create_task(
            client.raw("temperature 3500", SocketType.HYPRSUNSET, 2.0, False)
        )
    else:
        asyncio.create_task(
            client.raw("temperature 6500", SocketType.HYPRSUNSET, 2.0, False)
        )


async def init() -> None:
    global client
    client = HyprlandClient()

    logger.debug("Loading variables")
    _active_workspace = await client.query("activeworkspace")
    active_workspace.value = int(_active_workspace["id"])
    active_workspace.ready()

    show_layout.value, active_layout.value = await get_active_layout(client)
    active_layout.ready()
    show_layout.ready()

    _active_workspaces = await get_active_workspaces(client)
    workspace_ids.value = set(_active_workspaces)
    workspace_ids.ready()

    try:
        _temperature = await client.raw(
            "temperature", SocketType.HYPRSUNSET, 2.0, True
        )
        if not _temperature.isdigit():
            logger.error("Invalid answer from hyprsunset: %s", _temperature)
        else:
            night_light.value = int(_temperature) < 6000
            night_light.watch(change_night_light)
            night_light.ready()
    except ConnectionRefusedError as e:
        logger.error("Couldn't connect to hyprsunset", exc_info=e)

    logger.debug("Creating hyprland watchers")
    client.watch("workspacev2", EventCallbacks.on_workspacev2)
    client.watch("focusedmonv2", EventCallbacks.on_focusedmonv2)
    client.watch("createworkspacev2", EventCallbacks.on_createworkspacev2)
    client.watch("destroyworkspacev2", EventCallbacks.on_destroyworkspacev2)
    client.watch("activelayout", EventCallbacks.on_activelayout)

    gaps_out_query = await client.query("getoption general:gaps_out")
    rounding_query = await client.query("getoption decoration:rounding")

    try:
        if isinstance(gaps_out_query, dict):
            if gaps_out_query.get("int"):
                HyprlandVars.gap = int(gaps_out_query["int"])
            elif gaps_out_query.get("custom"):
                HyprlandVars.gap = int(gaps_out_query["custom"].split()[0])

        if isinstance(rounding_query, dict) and rounding_query.get("int"):
            HyprlandVars.rounding = rounding_query["int"]
    except Exception as e:
        logger.error(
            "Error while parsing gaps_out or rounding: %s",
            e, exc_info=e
        )


class HyprlandService(AsyncService):
    async def app_init(self):
        await init()

    async def start(self) -> None:
        global client
        logger.debug("Connecting to hyprland")
        await client.connect()
