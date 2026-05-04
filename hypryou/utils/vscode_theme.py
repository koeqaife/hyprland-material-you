import os
from pathlib import Path
import shutil
import logging

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
    
    source_time = source.stat().st_mtime
    dest_time = dest.stat().st_mtime
    
    return dest_time >= source_time

def copy_extension():
    home = Path.home()
    source = Path("/usr/lib/hypryou/hypryouvscode")
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

    if is_up_to_date(source, dest):
        logger.info(f"Theme for {editor} is already up to date. Skipping...")
        return

    logger.info(f"Updating theme for {editor}...")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source, dest)
