import subprocess
from pathlib import Path


def get() -> dict[str, str]:
    result = subprocess.run(
        ["cliphist", "list"],
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    )
    output = result.stdout.strip()
    data = {}

    for line in output.splitlines():
        try:
            id, content = line.split(maxsplit=1)
            data[id.strip()] = content.strip()
        except ValueError:
            continue

    return data


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
    output_file = Path(f"/tmp/hypryou/cliphist/{item_id}.png")
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
