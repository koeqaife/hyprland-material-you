function hypryou_colors --description "Load HyprYou colors into fish"
    set -l json ~/.cache/hypryou/colors/colors.json

    if not test -f $json
        return
    end

    # Determine palette inside jq
    set -l palette (jq -r 'if .is_dark == true then "dark" else "light" end' $json)

    # Extract colors using jq variables
    set -g hypr_primary      (jq -r --arg p "$palette" '.[$p].primary'      $json)
    set -g hypr_surface      (jq -r --arg p "$palette" '.[$p].surface'      $json)
    set -g hypr_onPrimary    (jq -r --arg p "$palette" '.[$p].onPrimary'    $json)
    set -g hypr_error        (jq -r --arg p "$palette" '.[$p].error'        $json)
    set -g hypr_tertiary     (jq -r --arg p "$palette" '.[$p].tertiary'     $json)

    # Apply to fish
    set -g fish_color_normal      $hypr_tertiary
    set -g fish_color_command     $hypr_primary
    set -g fish_color_param       $hypr_tertiary
    set -g fish_color_error       $hypr_error
end
