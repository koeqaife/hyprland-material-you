#!/bin/bash
gcc -Wall -Wextra -Wpedantic -Wshadow -Wformat=2 -Wcast-align -Wconversion -Wstrict-overflow=5 -O3 -march=native -flto -fno-plt client.c -o hypryouctl
gcc -O3 -march=native -flto -fno-plt $(pkg-config --cflags --libs gtk4) -Wall -Wextra -Wpedantic -Wshadow -Wformat=2 -Wcast-align -Wconversion -Wstrict-overflow=5 -o hypryou-start hypryou-start.c
gcc -O3 -march=native -flto -fno-plt $(pkg-config --cflags --libs gtk4) -Wall -Wextra -Wpedantic -Wshadow -Wformat=2 -Wcast-align -Wconversion -Wstrict-overflow=5 -o hypryou-crash-dialog crash-dialog.c
