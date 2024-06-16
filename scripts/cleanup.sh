#!/bin/bash
echo ":: Cleanup"

sudo pacman -Rns $(pacman -Qtdq)

yay -Scc
