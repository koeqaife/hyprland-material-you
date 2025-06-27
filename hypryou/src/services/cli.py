import os
import asyncio
from config import socket_path
from utils.logger import logger
import socket
from config import Settings
from utils import reload_css
from utils.service import AsyncService
from src.services.mpris import current_player
import subprocess
import shlex
from src.services import state
import shutil
import traceback
import typing as t


screenshot_mode_args = {
    "region": "-m region",
    "active": "-m active -m output",
    "window": "-m window"
}

HELP = {
    "ping": "Respond with Pong",
    "reload": "Reload UI",
    "exit": "Exit UI",
    "sync_settings": "Apply settings.json changes",
    "toggle_window": "Toggle window/popup visibility",
    "open_window": "Open window/popup",
    "close_window": "Close window/popup",
    "reload_css": "Reload CSS styles",
    "player": "Mini playerctl: play-pause, pause, next, prev, play",
    "apps": "Launch apps: files, editor, terminal, browser",
    "lock": "Lock session",
    "screenshot": ("Take screenshot: region, active, " +
                   "window; add freeze to pause screen"),
    "help": "Show this help"
}


def launch_detached(exec: str) -> None:
    cmd = shlex.split(exec)
    cwd = os.path.expanduser("~")

    subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid,
        cwd=cwd,
        env=os.environ.copy()
    )


class CliRequest:
    def __init__(self) -> None:
        pass

    def do_ping(self, args: str) -> str:
        return "pong"

    def do_reload(self, args: str) -> str:
        return "ok"

    def post_reload(self, args: str) -> None:
        exit(100)

    def do_exit(self, args: str) -> str:
        return "ok"

    def post_exit(self, args: str) -> None:
        exit(0)

    def do_sync_settings(self, args: str) -> str:
        Settings().sync()
        return "ok"

    def do_toggle_window(self, window_name: str) -> str:
        state.toggle_window(window_name)
        return "ok"

    def do_close_window(self, window_name: str) -> str:
        state.close_window(window_name)
        return "ok"

    def do_open_window(self, window_name: str) -> str:
        state.open_window(window_name)
        return "ok"

    def do_reload_css(self, args: str) -> str:
        reload_css()
        return "ok"

    def do_player(self, action: str) -> str:
        if not current_player.value:
            return "no players"
        current = current_player.value[1]
        actions = {
            "play-pause": current.play_pause,
            "play": current.play,
            "pause": current.pause,
            "next": current.next,
            "previous": current.previous
        }
        actions[action]()
        return "ok"

    def do_apps(self, app: str) -> str:
        settings = Settings()
        apps = {
            "files": settings.get("files"),
            "editor": settings.get("editor"),
            "terminal": settings.get("terminal"),
            "browser": settings.get("browser"),
        }
        exec = apps.get(app)
        if exec is not None:
            launch_detached(exec)
        else:
            _apps = ", ".join(apps.keys())
            return f"Couldn't find app {repr(app)}.\nAll apps: {_apps}"
        return "ok"

    def do_lock(self, args: str) -> str:
        state.is_locked.value = True
        return "ok"

    def do_screenshot(self, _mode: str) -> str:
        mode = _mode.split()[0] if _mode else "region"
        if mode not in screenshot_mode_args:
            modes = ", ".join(screenshot_mode_args.keys())
            return f"Couldn't find mode {mode}. All modes: {modes}"
        args = []
        args.append(screenshot_mode_args[mode])
        if "freeze" in _mode:
            args.append("--freeze")
        if shutil.which("swappy"):
            args.append("--raw")
            command = f"bash -c \"hyprshot {" ".join(args)} | swappy -f -\""
            launch_detached(command)
        else:
            command = f"bash -c \"hyprshot {" ".join(args)}\""
            launch_detached(command)
        return "ok"

    def do_help(self, args: str) -> None:

        max_cmd_len = max((len(cmd) for cmd in HELP), default=0)
        output = ""
        for cmd, help in HELP.items():
            padding = " " * (max_cmd_len - len(cmd))
            output += f"{cmd}{padding} -> {help}\n"
        return output


async def handle_client(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    try:
        data = await reader.read(1024)
        message = data.decode()
        if __debug__:
            logger.debug("Received message from socket: '%s'", message)

        response, post = await handle_request(message)
        writer.write(response.encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()
        if post is not None:
            post()
    except (
        ConnectionResetError,
        ConnectionRefusedError,
        ConnectionError,
        ConnectionAbortedError,
    ) as e:
        logger.debug("Cli command connection was closed with error: %s", e)
        if writer:
            writer.close()
            await writer.wait_closed()


async def handle_request(data: str) -> tuple[str, t.Callable[[], None] | None]:
    parts = data.strip().split(" ", 1)
    command = parts[0]
    args = parts[1] if len(parts) > 1 else ""
    attr = "do_" + command
    post_attr = "post_" + command
    request = CliRequest()
    try:
        if hasattr(request, attr):
            method = getattr(request, attr)
            post_method = getattr(request, post_attr, None)
            if callable(method):
                return (
                    str(method(args)),
                    lambda: post_method(args)
                    if post_method and callable(post_method)
                    else None
                )
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(
            "Error while calling %s", attr,
            exc_info=e
        )
        return tb, None
    return "unknown request", None


def is_socket_exists() -> bool:
    if not os.path.exists(socket_path):
        return False

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect(socket_path)
        sock.close()
        return True
    except (socket.error, OSError):
        return False


def create_socket_directory() -> None:
    socket_dir = os.path.dirname(socket_path)
    if not os.path.exists(socket_dir):
        os.makedirs(socket_dir)
        if __debug__:
            logger.debug(f"Created directory for socket at {socket_dir}")


class CliService(AsyncService):
    def __init__(self) -> None:
        self.server: asyncio.Server | None = None

    async def app_init(self) -> None:
        if not __debug__:
            # Skip checks in production mode
            return
        for attr in dir(CliRequest):
            if attr.startswith("do_"):
                cmd = attr.removeprefix("do_")
                if cmd not in HELP.keys():
                    logger.warning(f"Command {attr} doesn't have description!")

        for cmd in HELP.keys():
            if not hasattr(CliRequest, "do_" + cmd):
                logger.warning(f"Command {cmd} is not implemented!")

    async def start(self) -> None:
        if os.path.exists(socket_path):
            os.remove(socket_path)

        create_socket_directory()
        self.server = await asyncio.start_unix_server(
            handle_client, path=socket_path
        )
        if __debug__:
            logger.debug("Listening socket on %s", socket_path)

        try:
            async with self.server:
                await self.server.serve_forever()
        finally:
            os.remove(socket_path)

    def on_close(self) -> None:
        if self.server:
            try:
                self.server.close()
            except Exception as e:
                logger.critical("Couldn't close unix-socket.", exc_info=e)
