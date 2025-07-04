#!/bin/bash

cd "$(dirname "$0")" || exit 1

python utils_cy/setup.py build_ext --build-lib utils_cy --build-temp utils_cy/build
rm -rf utils_cy/build
