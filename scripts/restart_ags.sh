#!/bin/bash
killall ags
sleep 1
hyprctl dispatch exec ags
