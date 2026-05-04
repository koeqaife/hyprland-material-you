import os
from pathlib import Path
import shutil

# Get the editor
def get_editor_type():
    home = Path.home()
    
    # Checking for the extensions folder specifically is safer
    if (home / ".vscode/extensions").exists():
        return "vscode"
    elif (home / ".vscode-oss/extensions").exists():
        return "codium"
    return None

def prevent_recopy(source, dest):
    # If the destination doesn't exist at all, we definitely need to copy
    if not dest.exists():
        return False
    
    # Get the last modification time of both
    source_time = os.path.getmtime(source)
    dest_time = os.path.getmtime(dest)
    
    # If source is newer than destination, return False (meaning "don't prevent")
    if source_time > dest_time:
        return False
        
    # If destination is newer or equal, we can safely prevent the recopy
    return True

def copy_extension(editor):
    home = Path.home()
    source = Path("/usr/lib/hypryou/hypryouvscode")
    
    if editor == "vscode":
        dest = home / ".vscode/extensions/hypryouvscode"
    else:
        dest = home / ".vscode-oss/extensions/hypryouvscode"

    if source.exists():
        if prevent_recopy(source, dest):
            print(f"Theme for {editor} is already up to date. Skipping...")
            return

        print(f"Updating theme for {editor}...")
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source, dest)
