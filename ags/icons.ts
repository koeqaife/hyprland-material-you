import { LabelProps } from "types/widgets/label"

const _icons_folder = `${App.configDir}/assets/icons`

export const MaterialIcon = (icon: string, size: string = "24px", props?: LabelProps) => Widget.Label({
    label: icon,
    class_name: "icon material_icon",
    css: `font-size: ${size};`,
    hpack: "center",
    vpack: "center",
    ...props
})
