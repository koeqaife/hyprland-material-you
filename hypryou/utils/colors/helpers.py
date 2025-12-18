
type IntFloat = int | float
type RGB = tuple[IntFloat, IntFloat, IntFloat]
type RGBA = tuple[IntFloat, IntFloat, IntFloat, IntFloat]


def rgb_to_hex(rgb: RGB) -> str:
    return '#{:02x}{:02x}{:02x}'.format(*rgb[:3])


def hex_to_rgb(hex_color: str) -> str:
    hex_color = hex_color.lstrip('#')

    if len(hex_color) == 3:
        hex_color = ''.join(ch * 2 for ch in hex_color)

    if len(hex_color) != 6:
        raise ValueError('Invalid hex color format')

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    return f'{r}, {g}, {b}'
