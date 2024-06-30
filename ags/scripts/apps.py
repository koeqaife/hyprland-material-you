import argparse
import re
import os

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument(
    '--browser', type=str, help="Change default browser"
)
group.add_argument(
    '--filemanager', type=str, help="Change file manager"
)
group.add_argument(
    '--editor', type=str, help="Change default editor"
)
group.add_argument(
    '--terminal', type=str, help="Change default terminal"
)
group.add_argument(
    '--get', type=str, help="Get default app",
    choices=["browser", "editor", "terminal", "filemanager"]
)

args = parser.parse_args()

browser: str = args.browser
filemanager: str = args.filemanager
editor: str = args.editor
terminal: str = args.terminal
get: str = args.get

value: str = (
    args.browser or args.filemanager or
    args.editor or args.terminal or args.get
)

u = os.path.expanduser

config_file = u("~/dotfiles/hypr/conf/apps.conf")


with open(config_file) as f:
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
    pattern = re.compile(r'^\s*env\s*=\s*(\w+)\s*,\s*(.*?)\s*#\s*!\s*-\s*@(\w+)\s*$', re.MULTILINE)  # noqa
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
        r'\s*,\s*)(.*?)\s*(#.*)?$', re.MULTILINE
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

    for key in associations[key]:
        env_str = replace_value(env_str, key, value)


def change_file(file: str, value: str):
    which(value)
    with open(file, 'w') as f:
        f.write(value)


browser_file = u("~/dotfiles/.settings/browser.sh")
editor_file = u("~/dotfiles/.settings/editor.sh")
filemanager_file = u("~/dotfiles/.settings/filemanager.sh")
terminal_file = u("~/dotfiles/.settings/terminal.sh")

if get:
    with open(globals()[f"{value}_file"]) as f:
        print(f.read().strip())
elif browser:
    change_association("browser", value)
    change_file(browser_file, value)
elif filemanager:
    change_association("filemanager", value)
    change_file(filemanager_file, value)
elif editor:
    change_association("editor", value)
    change_file(editor_file, value)
elif terminal:
    change_association("terminal", value)
    change_file(terminal_file, value)


if env_str != original_env_str:
    with open(config_file, 'w') as f:
        f.write(env_str + '\n')
