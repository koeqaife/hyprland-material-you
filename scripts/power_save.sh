#!/bin/bash

STATE_FILE="/tmp/powersave_mode.state"

max_gpu_freq=$(cat /sys/class/drm/card0/gt_boost_freq_mhz)
min_gpu_freq=$(cat /sys/class/drm/card0/gt_min_freq_mhz)

enable_powersave() {
    cpu_count=$(grep -c ^processor /proc/cpuinfo)
    ondemand_cpu_count=1
    schedutil_cpu_count=0
    conservative_cpu_count=0
    
    for ((i=0; i<ondemand_cpu_count; i++)); do
        echo 'ondemand' > "/sys/devices/system/cpu/cpu$i/cpufreq/scaling_governor"
        echo 'power' > "/sys/devices/system/cpu/cpu$i/cpufreq/energy_performance_preference"
        echo $i 'ondemand'
        echo $i 'power'
    done

    for ((i=ondemand_cpu_count; i<ondemand_cpu_count + schedutil_cpu_count; i++)); do
        echo 'schedutil' > "/sys/devices/system/cpu/cpu$i/cpufreq/scaling_governor"
        echo 'power' > "/sys/devices/system/cpu/cpu$i/cpufreq/energy_performance_preference"
        echo $i 'schedutil'
        echo $i 'power'
    done

    for ((i=ondemand_cpu_count + schedutil_cpu_count; i<ondemand_cpu_count + schedutil_cpu_count + conservative_cpu_count; i++)); do
        echo 'conservative' > "/sys/devices/system/cpu/cpu$i/cpufreq/scaling_governor"
        echo 'power' > "/sys/devices/system/cpu/cpu$i/cpufreq/energy_performance_preference"
        echo $i 'conservative'
        echo $i 'power'
    done

    for ((i=ondemand_cpu_count + schedutil_cpu_count + conservative_cpu_count; i<cpu_count; i++)); do
        echo 'powersave' > "/sys/devices/system/cpu/cpu$i/cpufreq/scaling_governor"
        echo 'power' > "/sys/devices/system/cpu/cpu$i/cpufreq/energy_performance_preference"
        echo $i 'powersave'
        echo $i 'power'
    done
    echo $min_gpu_freq > /sys/class/drm/card0/gt_max_freq_mhz
    echo card0 $(cat /sys/class/drm/card0/gt_max_freq_mhz)
}

disable_powersave() {
    for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        echo 'performance' > "$cpu"
    done
    for cpu in /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference; do
        echo 'balance_performance' > "$cpu"
    done
    echo $max_gpu_freq > /sys/class/drm/card0/gt_max_freq_mhz
    echo card0 $(cat /sys/class/drm/card0/gt_max_freq_mhz)
}

if [ -f "$STATE_FILE" ] && grep -qx "enabled" "$STATE_FILE"; then
    disable_powersave
    echo "disabled" > "$STATE_FILE"
    echo "disabled"
else
    enable_powersave
    echo "enabled" > "$STATE_FILE"
    echo "enabled"
fi

exit 0
