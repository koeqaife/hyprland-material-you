import sys
import subprocess
import os
import json
import pathlib
import shutil

pathname = os.path.dirname(sys.argv[0])
homeFolder = os.path.expanduser('~')
dotfiles = homeFolder + "/dotfiles/"

result = subprocess.run(["bash", dotfiles + "hypr/scripts/monitors.sh"], capture_output=True, text=True)
monitors_json = result.stdout.strip()
monitors_arr = json.loads(monitors_json)
for row in monitors_arr:
    if row["focused"]:
        print(row["id"])
