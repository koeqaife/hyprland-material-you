#!/bin/bash

get() {
    cliphist list | iconv -f ISO-8859-1 -t UTF-8 -c
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
