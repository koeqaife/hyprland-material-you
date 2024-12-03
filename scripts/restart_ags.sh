#!/bin/bash
killall agsv1
sleep 1
hyprctl dispatch exec agsv1
