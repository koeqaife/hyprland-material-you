#!/bin/bash

get() {
    clip_list=$(cliphist list)

    while IFS= read -r line; do
        echo "$line" | iconv -t UTF-8
    done <<<"$clip_list"
}

copy_by_id() {
    id=$1
    cliphist decode $id | wl-copy
}

if [[ "$1" == "--get" ]]; then
    get
elif [[ "$1" == "--copy-by-id" ]]; then
    { copy_by_id "$2"; }
fi
