cimport cython

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef list[tuple[int, int, int]] downsample_image_rgb(str path, int quality):
    from PIL import Image
    cdef:
        int x, y, width, height
        int r, g, b
        list[tuple[int, int, int]] result = []

    img = Image.open(path).convert('RGB')
    width, height = img.size
    pix = img.load()

    for y in range(0, height, quality):
        for x in range(0, width, quality):
            r, g, b = pix[x, y]
            result.append((r, g, b))

    return result

cpdef bytearray argb_to_rgba(bytearray data):
    cdef Py_ssize_t i, size = len(data)
    cdef unsigned char tmp

    for i in range(0, size, 4):
        tmp = data[i]              # A
        data[i] = data[i + 1]      # R
        data[i + 1] = data[i + 2]  # G
        data[i + 2] = data[i + 3]  # B
        data[i + 3] = tmp          # A

    return data
