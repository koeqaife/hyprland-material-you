import os
from pathlib import Path
import typing as t

from repository import gio, glib
from config import APP_CACHE_DIR
from utils.logger import logger
import threading
import shutil

type Callback = t.Callable[[t.Optional[str]], None]

_download_locks: dict[str, list[Callback]] = {}
_download_mutex = threading.Lock()

MAGIC_NUMBERS = {
    b'\x89PNG\r\n\x1a\n': 'png',
    b'\xff\xd8\xff': 'jpg',
    b'GIF87a': 'gif',
    b'GIF89a': 'gif',
    b'RIFF': 'webp',
    b'BM': 'bmp',
    b'II*\x00': 'tiff',
    b'MM\x00*': 'tiff',
    b'\x00\x00\x01\x00': 'ico',
}


def guess_image_extension(filepath: str) -> str | None:
    path = Path(filepath)
    try:
        with path.open("rb") as f:
            header = f.read(16)
    except Exception:
        return None

    for magic, ext in MAGIC_NUMBERS.items():
        if header.startswith(magic):
            if ext == 'webp' and b'WEBP' not in header:
                continue
            return ext
    return None


def get_cache_dir(url: str, subdir: str) -> str:
    name = os.path.basename(url).replace("/", "_")
    return os.path.join(APP_CACHE_DIR, subdir, name)


def resize_image(
    filepath: str,
    size: tuple[int, int],
    with_unsharp: bool = True
) -> str:
    import pyvips
    target_w, target_h = size
    image = pyvips.Image.new_from_file(filepath, access="sequential")

    src_w, src_h = image.width, image.height
    tgt_ratio = target_w / target_h
    src_ratio = src_w / src_h

    if src_ratio > tgt_ratio:
        new_w = int(src_h * tgt_ratio)
        new_h = src_h
        left = (src_w - new_w) // 2
        top = 0
    else:
        new_h = int(src_w / tgt_ratio)
        new_w = src_w
        left = 0
        top = (src_h - new_h) // 2

    image = image.crop(left, top, new_w, new_h)
    scale = target_w / image.width
    image = image.resize(scale, kernel="lanczos3")

    if with_unsharp:
        image = image.sharpen()

    _ext = guess_image_extension(filepath)
    if _ext:
        ext = f".{_ext}"
        if ext == ".jpg" and filepath.endswith(".jpeg"):
            pass
        elif not filepath.endswith(ext):
            filepath += ext

    image.write_to_file(filepath)
    del image

    return filepath


def finalize_image_file(temp_path: str) -> str:
    import uuid
    import pyvips
    dir_path = Path(temp_path).parent
    unique_path = dir_path / str(uuid.uuid4())
    Path(temp_path).rename(unique_path)

    image = pyvips.Image.new_from_file(str(unique_path), access="sequential")

    ext = unique_path.suffix.lower() if unique_path.suffix else ".jpeg"
    final_path = dir_path / f"image{ext}"

    image.write_to_file(str(final_path))
    unique_path.unlink()
    del image
    return str(final_path)


class DownloadState:
    __slots__ = (
        "stream", "temp_path",
        "on_complete", "file",
        "__weakref__"
    )

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
                4096,
                glib.PRIORITY_DEFAULT,
                None,
                self.read_chunk,
                None
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
):
    file = gio.File.new_for_uri(url)

    def on_read(
        fileobj: gio.File,
        result: gio.AsyncResult,
        _data: t.Any
    ) -> DownloadState | None:
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

        if not os.path.exists(path):
            callback(None)
            return

        ext = os.path.splitext(path)[1]
        temp_path = os.path.join(cache_dir, f"image{ext}")
        os.makedirs(cache_dir, exist_ok=True)
        
        try:
            shutil.copy(path, temp_path)
        except FileNotFoundError:
            callback(None)
            return

        if size:
            temp_path = resize_image(temp_path, size)

        callback(temp_path)
        return

    temp_path = os.path.join(cache_dir, "temp")
    _key = f"{url}{size}"

    with _download_mutex:
        if _key in _download_locks:
            _download_locks[_key].append(callback)
            return
        else:
            _download_locks[_key] = [callback]

    def finish(path: t.Optional[str]) -> None:
        if path and size:
            path = resize_image(path, size)

        with _download_mutex:
            callbacks = _download_locks.pop(_key, [])
        for cb in callbacks:
            cb(path)

    if __debug__:
        logger.debug("Downloading new image")
    os.makedirs(cache_dir, exist_ok=True)
    download_file_async(url, temp_path, finish)
