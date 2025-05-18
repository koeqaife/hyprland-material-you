from __future__ import annotations

import subprocess
from pathlib import Path
from utils import Ref
import os
from config import APP_CACHE_PATH

TEMP_PATH = os.path.join(APP_CACHE_PATH, "cliphist")
items = Ref[dict[str, str]]({}, name="cliphist_items")


def get() -> dict[str, str]:
    result = subprocess.run(
        ["cliphist", "list"],
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    )

    lines = result.stdout.strip().splitlines()[:250]

    return {
        id_.strip(): content.strip()
        for line in lines
        if (parts := line.split(maxsplit=1)) and len(parts) == 2
        for id_, content in [parts]
    }


def repopulate() -> None:
    history = get()
    history_keys = set(history.keys())
    existing_keys = set(items.value.keys())

    new_keys = history_keys - existing_keys
    removed_keys = existing_keys - history_keys

    if not new_keys and not removed_keys:
        return

    items._signals.block("changed")

    for key in new_keys:
        items.value[key] = history[key]

    for key in removed_keys:
        del items.value[key]

    items._signals.unblock("changed")
    items._signals.notify("changed", items.value)


def copy_by_id(item_id: str) -> None:
    with subprocess.Popen(
        ["cliphist", "decode", item_id], stdout=subprocess.PIPE
    ) as decode_proc, subprocess.Popen(
        ["wl-copy"], stdin=decode_proc.stdout
    ):
        if decode_proc.stdout:
            decode_proc.stdout.close()


def clear() -> None:
    subprocess.run(["cliphist", "wipe"], check=True)


def save_cache_file(item_id: str) -> str:
    output_file = Path(f"{TEMP_PATH}/{item_id}.png")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if not output_file.exists():
        with subprocess.Popen(
            ["cliphist", "decode", item_id], stdout=subprocess.PIPE
        ) as decode_proc, open(output_file, "wb") as file:
            if decode_proc.stdout:
                file.write(decode_proc.stdout.read())

    return str(output_file)


def clear_tmp() -> None:
    tmp_dir = Path("/tmp/hypryou/cliphist/")
    for file in tmp_dir.glob("*"):
        file.unlink()
