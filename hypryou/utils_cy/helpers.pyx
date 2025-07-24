
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
