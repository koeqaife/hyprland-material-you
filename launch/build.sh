gcc -o hypryou-start hypryou-start.c $(pkg-config --cflags --libs gtk4)
gcc -o hypryou-crash-dialog crash-dialog.c $(pkg-config --cflags --libs gtk4)
