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

def is_up_to_date(source: Path, dest: Path):
    if not dest.exists():
        return False
    # Check if source was modified more recently than destination
    return dest.stat().st_mtime >= source.stat().st_mtime

def ensure_symlink(cache_file: Path, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        if target.is_symlink() and target.resolve() == cache_file:
            return
        # If it's a real file or a dead link, remove it to make room for the correct symlink
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
    target.symlink_to(cache_file)

def update_theme(script_path: Path):
    """Runs the node script to re-generate the theme based on the new colors.json"""
    try:
        result = subprocess.run(
            ["node", str(script_path)],
            capture_output=True,
            text=True,
            check=True # Raises CalledProcessError if returncode != 0
        )
        logger.info("Theme generated successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Theme generator failed:\n{e.stderr}")
    except FileNotFoundError:
        logger.error("Node.js not found. Please install node to generate VS Code themes.")

def copy_extension():
    home = Path.home()
    source = Path("/usr/lib/hypryou/themes/marmarek-here.hypryouvscode-1.0.1")
    cache_colors = home / ".cache/hypryou/colors/colors.json"

    editor = get_editor_type()
    if not editor:
        logger.error("No VS Code or Codium directory found!")
        return

    dest = home / (f".{editor}/extensions/marmarek-here.hypryouvscode-1.0.1")
    
    # 1. Sync extension files
    if not source.exists():
        logger.error(f"Source extension not found at {source}")
        return

    if not is_up_to_date(source, dest):
        logger.info(f"Updating theme files for {editor}...")
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source, dest)

    # 2. Link the generated colors
    theme_colors_target = dest / "themes/colors.json"
    if cache_colors.exists():
        ensure_symlink(cache_colors, theme_colors_target)
    else:
        logger.error("Cache colors.json not found. Run the color generator first.")
        return

    # 3. Trigger Node.js generation
    script = dest / "scripts" / "generate-theme.mjs"
    if script.exists():
        update_theme(script)
    else:
        logger.error("Theme generator script (generate-theme.mjs) missing in extension")
