import os
import asyncio
from config import socket_path
from utils.logger import logger
import socket
from config import Settings
from src.variables import Globals
from src.services.events import Event
from utils import apply_css
from utils.service import AsyncService


class CliRequest:
    def __init__(self) -> None:
        pass

    def do_ping(self, args: str) -> str:
        return "pong"

    def do_reload(self, args: str) -> str:
        exit(100)

    def do_exit(self, args: str) -> str:
        exit(0)

    def do_sync_settings(self, args: str) -> str:
        Settings().sync()
        return "ok"

    def do_toggle_window(self, args: str) -> str:
        event = Event(None, args, "toggle_window")
        Globals.events.notify(event)
        return "ok"

    def do_reload_css(self, args: str) -> str:
        apply_css()
        return "ok"


async def handle_client(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    try:
        data = await reader.read(1024)
        message = data.decode()
        logger.debug("Received message from socket: '%s'", message)

        response = await handle_request(message)
        writer.write(response.encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()
    except (
        ConnectionResetError,
        ConnectionRefusedError,
        ConnectionError,
        ConnectionAbortedError,
    ) as e:
        logger.debug("Cli command connection was closed with error: %s", e)
        if writer:
            writer.close()


async def handle_request(data: str) -> str:
    command, args = data.split(" ", 1) if " " in data else (data, "")
    attr = "do_" + command
    request = CliRequest()
    if hasattr(request, attr):
        method = getattr(request, attr)
        if callable(method):
            return str(method(args))
    return "unknown request"


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
        logger.debug(f"Created directory for socket at {socket_dir}")


class CliService(AsyncService):
    def __init__(self) -> None:
        self.server: asyncio.Server | None = None

    async def start(self) -> None:
        if os.path.exists(socket_path):
            os.remove(socket_path)

        create_socket_directory()
        self.server = await asyncio.start_unix_server(
            handle_client, path=socket_path
        )
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
