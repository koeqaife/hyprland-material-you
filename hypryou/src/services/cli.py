import os
import asyncio
from config import socket_path
from utils.logger import logger
import socket


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter
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
        ConnectionAbortedError
    ) as e:
        logger.debug("Cli command connection was closed with error: %s", e)
        if writer:
            writer.close()


async def handle_request(data: str) -> str:
    if data == "ping":
        return "pong"
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


async def serve() -> None:
    if os.path.exists(socket_path):
        os.remove(socket_path)

    create_socket_directory()
    server = await asyncio.start_unix_server(handle_client, path=socket_path)
    logger.debug("Listening socket on %s", socket_path)

    try:
        async with server:
            await server.serve_forever()
    finally:
        os.remove(socket_path)
