from libc.stdlib cimport malloc, free

cdef inline int min3(int a, int b, int c) nogil:
    return a if a < b and a < c else b if b < c else c

cdef inline int max3(int a, int b, int c) nogil:
    return a if a > b and a > c else b if b > c else c

cdef inline int min2(int a, int b) nogil:
    return a if a < b else b

cdef inline int max2(int a, int b) nogil:
    return a if a > b else b

cpdef int levenshtein_distance(str s1, str s2):
    cdef int len1 = len(s1)
    cdef int len2 = len(s2)
    cdef int i, j

    if len1 == 0:
        return len2
    if len2 == 0:
        return len1

    cdef int **matrix = <int**>malloc((len1 + 1) * sizeof(int*))
    for i in range(len1 + 1):
        matrix[i] = <int*>malloc((len2 + 1) * sizeof(int))
        for j in range(len2 + 1):
            matrix[i][j] = 0

    for i in range(len1 + 1):
        matrix[i][0] = i
    for j in range(len2 + 1):
        matrix[0][j] = j

    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            matrix[i][j] = min3(
                matrix[i - 1][j] + 1,
                matrix[i][j - 1] + 1,
                matrix[i - 1][j - 1] + cost
            )

    cdef int result = matrix[len1][len2]

    for i in range(len1 + 1):
        free(matrix[i])
    free(matrix)

    return result

cdef float partial_ratio(str short_s, str long_s):
    cdef int len_s = len(short_s)
    cdef int len_l = len(long_s)
    cdef int i, dist
    cdef float best = 0.0
    cdef str sub
    cdef float score
    if len_s == 0:
        return 1.0
    for i in range(len_l - len_s + 1):
        sub = long_s[i:i + len_s]
        dist = levenshtein_distance(short_s, sub)
        score = 1.0 - (dist / len_s)
        if score > best:
            best = score
    return best

cpdef float compute_score(str s1, str s2):
    if s1 == s2:
        return 1.0

    cdef int dist = levenshtein_distance(s1, s2)
    cdef float max_len = max2(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    cdef float full = 1.0 - (dist / max_len)

    cdef float part = 0.0
    if len(s1) < len(s2):
        part = partial_ratio(s1, s2)
    elif len(s2) < len(s1):
        part = partial_ratio(s2, s1)

    cdef float score = 0.85 * full + 0.15 * part

    if s1 and s2 and s1[0] != s2[0]:
        score -= 0.05

    cdef int len_diff = abs(len(s1) - len(s2))
    if len_diff >= 3:
        score -= 0.05 * len_diff / max_len

    cdef int common_prefix_len = 0
    cdef int min_len = min(len(s1), len(s2))
    for i in range(min_len):
        if s1[i] == s2[i]:
            common_prefix_len += 1
        else:
            break
    score += 0.02 * common_prefix_len

    if s1 in s2 or s2 in s1:
        score += 0.06

    if score > 1.0:
        score = 1.0
    elif score < 0.0:
        score = 0.0

    return score
