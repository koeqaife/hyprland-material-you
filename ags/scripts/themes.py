# by koeqaife ;)

import re
import os
import argparse
from typing import Dict
import json
from itertools import islice


# HERE'S ConfigVersion FOR THEMES
CONFIG_VERSION = "2"

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("-a", "--folder", type=str)
group.add_argument("-f", "--file", type=str)
group.add_argument("-c", "--current-version", action="store_true")

args = parser.parse_args()

folder: str = args.folder
file: str = args.file
current: str = args.current_version


default_dict = {
    "name": "None",
    "author": "Unknown",
    "version": "1.0.0",
    "config_version": "0",
    "load_default_css": "true",
    "description": "No description",
    "hide": "false"
}
is_bool = ["load_default_css", "hide"]


def to_snake_case(string: str) -> str:
    string = re.sub(r'(?<!^)(?=[A-Z])', '_', string).lower()
    string = string.replace("-", "_")
    return string


def process_dict(dict: dict) -> dict:
    _dict = {
        to_snake_case(key): value
        for key, value in dict.items()
    }

    if "name" not in _dict and "path" in _dict:
        _dict["name"] = os.path.basename(_dict["path"])

    if "path" in _dict:
        _dict["path"] = os.path.abspath(_dict["path"])

    for key, value in default_dict.items():
        _dict.setdefault(key, value)

    for key in is_bool:
        _dict[key] = str(_dict.get(key)).lower() == "true"

    return _dict


def extract_comment_values(file_path: str) -> Dict[str, str]:
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = list(islice(file, 25))
        content = ''.join(lines)

    comment_match = re.search(r'/\*\*(.*?)\*/', content, re.DOTALL)
    if not comment_match:
        return {"path": file_path}

    comment = comment_match.group(1).strip()

    pattern = re.compile(r'^\s*\*\s*(\w+):\s*(.+)$', re.MULTILINE)
    _dict = dict(pattern.findall(comment))
    _dict["path"] = file_path
    return _dict


def check_all_files(dir: str):
    files = [os.path.join(dir, f) for f in os.listdir(dir)
             if os.path.isfile(os.path.join(dir, f))
             and f.endswith(".css")]
    info = []
    for x in files:
        info.append(process_dict(extract_comment_values(x)))

    return info


if __name__ == "__main__":
    result = None
    if folder:
        result = check_all_files(folder)
    elif file:
        result = process_dict(extract_comment_values(file))
    elif current:
        print(CONFIG_VERSION)
        exit(0)

    print(json.dumps(result))
