import argparse
import os
import re
import json

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--browser', type=str, help="Change default browser")
group.add_argument('--filemanager', type=str, help="Change file manager")
group.add_argument('--editor', type=str, help="Change default editor")
group.add_argument('--terminal', type=str, help="Change default terminal")
group.add_argument('--get', type=str, help="Get default app",
                   choices=["browser", "editor", "terminal", "filemanager"])

args = parser.parse_args()

browser = args.browser
filemanager = args.filemanager
editor = args.editor
terminal = args.terminal
get = args.get

value = (args.browser or args.filemanager or
         args.editor or args.terminal or args.get)

u = os.path.expanduser

CONFIG_FILE = u("~/dotfiles/hypr/conf/apps.conf")
JSON_CONFIG_FILE = u("~/dotfiles/.settings/apps.json")

with open(CONFIG_FILE) as f:
    original_env_str = f.read().strip()
    env_str = original_env_str


def which(program: str):
    def is_executable(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_executable(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_executable(exe_file):
                return exe_file
    raise ProgramNotFound(value)


def extract_associations(env_str):
    pattern = re.compile(
        r'^\s*env\s*=\s*(\w+)\s*,\s*(.*?)\s*#\s*!\s*-\s*@(\w+)\s*$',
        re.MULTILINE
    )
    associations = {}
    matches = pattern.findall(env_str)
    for key, _, association in matches:
        if association not in associations:
            associations[association] = []
        if key not in associations[association]:
            associations[association].append(key)
    return associations


associations = extract_associations(env_str)


def replace_value(env_str, key, new_value):
    pattern = re.compile(
        r'^(\s*env\s*=\s*' +
        re.escape(key) +
        r'\s*,\s*)(.*?)\s*(#.*)?$',
        re.MULTILINE
    )
    return re.sub(pattern, r'\1' + new_value + r'  \3', env_str)


class AssociationNotFound(Exception):
    def __init__(self, name: str, *args: object) -> None:
        error = f"{name} association not found, \n{associations}"
        super().__init__(error, *args)


class ProgramNotFound(Exception):
    def __init__(self, name: str, *args: object) -> None:
        error = f"{name} not found"
        super().__init__(error, *args)


def change_association(key: str, value: str):
    global env_str
    which(value)
    if key not in associations:
        raise AssociationNotFound(key)

    for assoc_key in associations[key]:
        env_str = replace_value(env_str, assoc_key, value)


def read_json_config():
    try:
        with open(JSON_CONFIG_FILE) as json_file:
            return json.load(json_file)
    except IOError as e:
        print(f"Error reading {JSON_CONFIG_FILE}: {e}")
        raise


def write_json_config(config):
    try:
        with open(JSON_CONFIG_FILE, 'w') as json_file:
            json.dump(config, json_file, indent=4)
    except IOError as e:
        print(f"Error writing to {JSON_CONFIG_FILE}: {e}")
        raise


def update_json_config(key: str, value: str):
    config = read_json_config()
    config[key] = value
    write_json_config(config)


if get:
    json_config = read_json_config()
    print(json_config[get])
elif browser:
    change_association("browser", value)
    update_json_config("browser", value)
elif filemanager:
    change_association("filemanager", value)
    update_json_config("filemanager", value)
elif editor:
    change_association("editor", value)
    update_json_config("editor", value)
elif terminal:
    change_association("terminal", value)
    update_json_config("terminal", value)

if env_str != original_env_str:
    with open(CONFIG_FILE, 'w') as f:
        f.write(env_str + '\n')
