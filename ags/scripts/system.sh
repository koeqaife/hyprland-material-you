#!/bin/bash

get_cpu_usage() {
  top -bn1 | grep "Cpu(s)" | \
  awk '{print $2 + $4}'
}

get_ram_usage() {
  free -m | awk 'NR==2{printf "Memory Usage: %.2f%%\n", $3*100/$2 }'
}

if [[ "$1" == "--cpu" ]]; then
	get_cpu_usage
elif [[ "$1" == "--ram" ]]; then
	get_ram_usage
fi
