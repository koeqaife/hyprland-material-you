import argparse
import re
import os
import json

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--browser', type=str, help="Change default browser")
group.add_argument('--filemanager', type=str, help="Change file manager")
group.add_argument('--editor', type=str, help="Change default editor")
group.add_argument('--terminal', type=str, help="Change default terminal")
group.add_argument('--get', type=str, help="Get default app", choices=["browser", "editor", "terminal", "filemanager"])

args = parser.parse_args()

config_file = os.path.expanduser("~/dotfiles/hypr/conf/apps.conf")
json_config_file = os.path.expanduser("~/dotfiles/ags/assets/apps.json")

def read_apps_conf():
    with open(config_file) as f:
        return f.read().strip()

def write_apps_conf(content):
    with open(config_file, 'w') as f:
        f.write(content + '\n')

def read_json_config():
    with open(json_config_file) as json_file:
        return json.load(json_file)

def write_json_config(config):
    with open(json_config_file, 'w') as json_file:
        json.dump(config, json_file, indent=4)

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
    pattern = re.compile(r'^\s*env\s*=\s*(\w+)\s*,\s*(.*?)\s*#\s*!\s*-\s*@(\w+)\s*$', re.MULTILINE)  # noqa
    associations = {}
    matches = pattern.findall(env_str)
    for key, _, association in matches:
        if association not in associations:
            associations[association] = []
        if key not in associations[association]:
            associations[association].append(key)
    return associations

def replace_value(env_str, key, new_value):
    pattern = re.compile(
        r'^(\s*env\s*=\s*' +
        re.escape(key) +
        r'\s*,\s*)(.*?)\s*(#.*)?$', re.MULTILINE
    )
    return re.sub(pattern, r'\1' + new_value + r'  \3', env_str)

class AssociationNotFound(Exception):
    def __init__(self, name: str, *args: object) -> None:
        error = f"{name} association not found"
        super().__init__(error, *args)

class ProgramNotFound(Exception):
    def __init__(self, name: str, *args: object) -> None:
        error = f"{name} not found"
        super().__init__(error, *args)

def change_association(key: str, value: str):
    env_str = read_apps_conf()
    which(value)
    associations = extract_associations(env_str)
    if key not in associations:
        raise AssociationNotFound(key)

    for key in associations[key]:
        env_str = replace_value(env_str, key, value)

    write_apps_conf(env_str)

def update_json_config(key: str, value: str):
    config = read_json_config()
    config[key] = value
    write_json_config(config)

if args.get:
    json_config = read_json_config()
    print(json_config[args.get])
elif args.browser:
    change_association("browser", args.browser)
    update_json_config("browser", args.browser)
elif args.filemanager:
    change_association("filemanager", args.filemanager)
    update_json_config("filemanager", args.filemanager)
elif args.editor:
    change_association("editor", args.editor)
    update_json_config("editor", args.editor)
elif args.terminal:
    change_association("terminal", args.terminal)
    update_json_config("terminal", args.terminal)
