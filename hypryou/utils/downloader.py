import os
import typing as t
import uuid

from repository import gio, glib
from PIL import Image, ImageFilter
from config import APP_CACHE_PATH
from utils.logger import logger
import threading

type Callback = t.Callable[[t.Optional[str]], None]

_download_locks: dict[str, list[Callback]] = {}
_download_mutex = threading.Lock()


def get_cache_dir(url: str, subdir: str) -> str:
    name = os.path.basename(url).replace("/", "_")
    return os.path.join(APP_CACHE_PATH, subdir, name)


def resize_image(
    filepath: str,
    size: tuple[int, int],
    with_unsharp: bool = True
) -> str:
    target_w, target_h = size

    with Image.open(filepath) as img:
        src_w, src_h = img.size
        tgt_ratio = target_w / target_h
        src_ratio = src_w / src_h

        if src_ratio > tgt_ratio:
            new_w = int(src_h * tgt_ratio)
            new_h = src_h
            left = (src_w - new_w) // 2
            top = 0
        else:
            new_w = src_w
            new_h = int(src_w / tgt_ratio)
            left = 0
            top = (src_h - new_h) // 2

        right = left + new_w
        bottom = top + new_h

        cropped = img.crop((left, top, right, bottom))

        resized = cropped.resize(size, Image.Resampling.LANCZOS)

        if with_unsharp:
            sharpened = resized.filter(
                ImageFilter.UnsharpMask(radius=1, percent=5, threshold=3)
            )
            sharpened.save(filepath, quality=95)
        else:
            resized.save(filepath, quality=95)

    return filepath


def finalize_image_file(temp_path: str) -> str:
    dir_path = os.path.dirname(temp_path)
    unique_path = os.path.join(dir_path, str(uuid.uuid4()))
    os.rename(temp_path, unique_path)
    with Image.open(unique_path) as img:
        ext = img.format.lower()
        final_path = os.path.join(dir_path, f"image.{ext}")
        img.save(final_path)
    os.remove(unique_path)
    return final_path


class DownloadState:
    def __init__(
        self,
        stream: gio.FileInputStream,
        temp_path: str,
        on_complete: Callback
    ) -> None:
        self.stream = stream
        self.temp_path = temp_path
        self.on_complete = on_complete
        self.file: t.BinaryIO | None = None

    def read_chunk(
        self,
        stream: gio.FileInputStream,
        res: gio.AsyncResult,
        _data: t.Any
    ) -> None:
        if not self.file:
            self.file = open(self.temp_path, "wb")
        try:
            chunk = stream.read_bytes_finish(res)
            if not chunk.get_size():
                self.file.close()
                self.file = None
                finalized_path = finalize_image_file(self.temp_path)
                self.stream.close_async(
                    glib.PRIORITY_DEFAULT, None, None, None
                )
                self.on_complete(finalized_path)
                return
            data = chunk.get_data()
            if not data:
                logger.warning("Chunk data is None!")
            else:
                self.file.write(data)
            self.stream.read_bytes_async(
                4096, glib.PRIORITY_DEFAULT, None, self.read_chunk, None
            )
        except Exception as e:
            logger.error("Couldn't read file chunk: %s", e, exc_info=e)
            self.stream.close_async(glib.PRIORITY_DEFAULT, None, None, None)
            self.on_complete(None)
            if self.file:
                self.file.close()
                self.file = None


def download_file_async(
    url: str,
    temp_path: str,
    on_complete: Callback
) -> None:
    file = gio.File.new_for_uri(url)

    def on_read(
        fileobj: gio.File,
        result: gio.AsyncResult,
        _data: t.Any
    ) -> None:
        try:
            stream = fileobj.read_finish(result)
            state = DownloadState(stream, temp_path, on_complete)
            stream.read_bytes_async(
                4096, glib.PRIORITY_DEFAULT, None, state.read_chunk, None
            )
        except Exception as e:
            logger.error("Couldn't download file: %s", e, exc_info=e)
            on_complete(None)

    file.read_async(glib.PRIORITY_DEFAULT, None, on_read, None)


def download_image_async(
    url: str,
    callback: Callback,
    size: tuple[int, int] | None = None,
    subdir: str = "images"
) -> None:
    if size:
        subdir = f"{subdir}/{size[0]}x{size[1]}"
    cache_dir = get_cache_dir(url, subdir)

    if os.path.exists(cache_dir):
        for fname in os.listdir(cache_dir):
            if fname.startswith("image."):
                callback(os.path.join(cache_dir, fname))
                return

    if url.startswith("file://"):
        path = gio.File.new_for_uri(url).get_path()
        if not path:
            callback(None)
            return
        if not size:
            callback(path)
            return

        path = resize_image(path, size)
        callback(path)
        return

    temp_path = os.path.join(cache_dir, "temp")

    with _download_mutex:
        if url in _download_locks:
            _download_locks[url].append(callback)
            return
        else:
            _download_locks[url] = [callback]

    def finish(path: t.Optional[str]) -> None:
        if path and size:
            path = resize_image(path, size)

        with _download_mutex:
            callbacks = _download_locks.pop(url, [])
        for cb in callbacks:
            cb(path)

    logger.debug("Downloading new image")
    os.makedirs(cache_dir, exist_ok=True)
    download_file_async(url, temp_path, finish)
