#!/bin/bash

get() {
    cliphist list | iconv -f $(locale charmap) -t UTF-8 -c
}

copy_by_id() {
    id=$1
    cliphist decode $id | wl-copy
}

clear() {
    cliphist wipe
}

save_cache_file() {
    id=$1

    output_file="/tmp/ags/cliphist/$id.png"

    if [[ ! -f "$output_file" ]]; then
        mkdir -p "/tmp/ags/cliphist/"
        cliphist decode "$id" >"$output_file"
    fi

    echo $output_file
}

clear_tmp() {
    rm "/tmp/ags/cliphist/*"
}

if [[ "$1" == "--get" ]]; then
    get
elif [[ "$1" == "--copy-by-id" ]]; then
    { copy_by_id "$2"; }
elif [[ "$1" == "--save-by-id" ]]; then
    { save_cache_file "$2"; }
elif [[ "$1" == "--clear-cache" ]]; then
    clear_tmp
elif [[ "$1" == "--clear" ]]; then
    clear
fi
