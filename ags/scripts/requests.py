import argparse
import json
import os
import sys

current_path = os.path.dirname(os.path.abspath(__file__))
sys.path.pop(0)

import requests  # noqa

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--post", type=str)
group.add_argument("--get", type=str)
group.add_argument("--put", type=str)
group.add_argument("--delete", type=str)
parser.add_argument("--json", type=str)
parser.add_argument("--headers", type=str)
parser.add_argument("--verify", type=bool, default=True)

args = parser.parse_args()

_verify = args.verify
_url: str = args.post or args.get or args.put or args.delete
_post = args.post is not None
_get = args.get is not None
_put = args.put is not None
_delete = args.delete is not None
_json: dict | None = (
    None if args.json is None
    else json.loads(args.json)
)
_headers: dict | None = (
    None if args.headers is None
    else json.loads(args.headers)
)


def main():
    _args = [_url]
    _kwargs = {
        "json": _json,
        "headers": _headers,
        "verify": _verify,
    }
    if _post:
        response = requests.post(*_args, **_kwargs)
    elif _get:
        response = requests.get(*_args, **_kwargs)
    elif _put:
        response = requests.put(*_args, **_kwargs)
    elif _delete:
        response = requests.delete(*_args, **_kwargs)
    return response


if __name__ == "__main__":
    r = main()
    _type = "text"
    _json = None
    text = r.text
    try:
        _json = json.loads(text)
        _type = "json"
    except Exception:
        ...

    print(json.dumps({
        "type": _type,
        "data": _json or text,
        "code": r.status_code
    }))
