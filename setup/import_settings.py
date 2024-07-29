import json
import os
from os import path
import shutil

settings = path.expanduser("~/dotfiles/.settings")
settings_json = f"{settings}/settings.json"
apps_json = f"{settings}/apps.json"


files = {
    "settings": {
        f"{settings}/custom-color": "custom-color",
        f"{settings}/swww-anim": "swww-anim",
        f"{settings}/color-scheme": "color-scheme",
        f"{settings}/generation-scheme": "generation-scheme",
        f"{settings}/wallpaper-engine.sh": "wallpaper-engine"
    },
    "apps": {
        f"{settings}/browser.sh": "browser",
        f"{settings}/editor.sh": "editor",
        f"{settings}/filemanager.sh": "filemanager",
        f"{settings}/terminal.sh": "terminal"
    }
}

if not path.isfile(settings_json):
    print(f":: File \"{settings_json}\" does not exist!")
    exit(1)
if not path.isfile(apps_json):
    print(f":: File \"{apps_json}\" does not exist!")
    exit(1)

print(":: Loading files")
with open(settings_json) as f:
    settings_c = json.load(f)
with open(apps_json) as f:
    apps_c = json.load(f)

print(":: Importing")
for file in files["apps"]:
    if path.isfile(file):
        with open(file) as f:
            apps_c[files["apps"][file]] = f.read().strip()
    else:
        print(f": File {file} doesn't exists")
for file in files["settings"]:
    if path.isfile(file):
        with open(file) as f:
            settings_c[files["settings"][file]] = f.read().strip()
    else:
        print(f": File {file} doesn't exists")

print(":: Saving")
with open(settings_json, 'w') as f:
    json.dump(settings_c, f, indent=2)
with open(apps_json, 'w') as f:
    json.dump(apps_c, f, indent=2)

print(":: Backing up old files")
old_files = [
    f for f in os.listdir(settings)
    if os.path.isfile(os.path.join(settings, f))
]
backup_folder = f"{settings}/old"
ignore = ["icon-theme", "settings.json", "apps.json"]
os.makedirs(backup_folder, exist_ok=True)
for x in old_files:
    if x.strip() not in ignore:
        shutil.move(f"{settings}/{x}", f"{backup_folder}/{x}")
