get_current_temperature() {
    busctl --user get-property rs.wl-gammarelay / rs.wl.gammarelay Temperature | awk '{print $2}'
}

day_temp=6500
night_temp=5000

current_temp=$(get_current_temperature)

if [ "$current_temp" -lt "$(( (day_temp + night_temp) / 2 ))" ]; then
    echo "enabled"
else
    echo "disabled"
fi