import os
from pathlib import Path
import shutil
import logging
import subprocess

logger = logging.getLogger(__name__)


def get_editor_type():
    home = Path.home()

    if (home / ".vscode/extensions").exists():
        return "vscode"
    elif (home / ".vscode-oss/extensions").exists():
        return "codium"
    return None


def is_up_to_date(source, dest):
    if not dest.exists():
        return False

    return dest.stat().st_mtime >= source.stat().st_mtime


def ensure_symlink(cache_file: Path, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)

    # If symlink exists but is wrong, remove it
    if target.exists() or target.is_symlink():
        if target.is_symlink() and target.resolve() == cache_file:
            return
        target.unlink()

    target.symlink_to(cache_file)


def copy_extension():
    home = Path.home()
    source = Path("/usr/lib/hypryou/themes/hypryouvscode")
    cache_colors = Path.home() / ".cache/hypryou/colors/colors.json"

    editor = get_editor_type()

    if editor == "vscode":
        dest = home / ".vscode/extensions/hypryouvscode"
    elif editor == "codium":
        dest = home / ".vscode-oss/extensions/hypryouvscode"
    else:
        logger.error("No editor found!")
        return

    dest.parent.mkdir(parents=True, exist_ok=True)

    if not source.exists():
        logger.error("Source extension not found")
        return

    # --- COPY STEP ---
    if not is_up_to_date(source, dest):
        logger.info(f"Updating theme files for {editor}...")
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source, dest)
    else:
        logger.info(f"Theme files already up to date for {editor}. Skipping copy...")

    # --- SYMLINK STEP (always ensure correct link) ---
    theme_colors_target = dest / "themes/colors.json"

    if cache_colors.exists():
        ensure_symlink(cache_colors, theme_colors_target)
        logger.info("Linked colors.json from cache")
    else:
        logger.error("Cache colors.json not found")
        return

    # --- GENERATION STEP (always run) ---
    script = dest / "scripts" / "generate-theme.mjs"

    if not script.exists():
        logger.error("Theme generator script not found in extension")
        return

    logger.info("Generating theme from cache...")

    result = subprocess.run(
        ["node", str(script)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        logger.error(f"Theme generator failed:\n{result.stderr}")
    else:
        logger.info("Theme generated successfully")
