from libc.stdlib cimport malloc, free
from cpython.unicode cimport PyUnicode_AsUTF8String

cdef inline int min3(int a, int b, int c) nogil:
    return a if a < b and a < c else b if b < c else c

cdef inline int max3(int a, int b, int c) nogil:
    return a if a > b and a > c else b if b > c else c

cdef inline int min2(int a, int b) nogil:
    return a if a < b else b

cdef inline int max2(int a, int b) nogil:
    return a if a > b else b

cdef inline float min2float(float a, float b) nogil:
    return a if a < b else b

cdef inline float max2float(float a, float b) nogil:
    return a if a > b else b

cpdef int levenshtein_distance(str s1, str s2):
    cdef int len1 = len(s1)
    cdef int len2 = len(s2)
    cdef int i, j, cost, tmp

    if len1 == 0:
        return len2
    if len2 == 0:
        return len1

    if len2 > len1:
        s1, s2 = s2, s1
        len1, len2 = len2, len1

    cdef bytes b1 = PyUnicode_AsUTF8String(s1)
    cdef bytes b2 = PyUnicode_AsUTF8String(s2)
    cdef const char* cs1 = b1
    cdef const char* cs2 = b2

    cdef int *prev = <int *>malloc((len2 + 1) * sizeof(int))
    cdef int *curr = <int *>malloc((len2 + 1) * sizeof(int))
    cdef int *tmp_ptr

    with nogil:
        for j in range(len2 + 1):
            prev[j] = j

        for i in range(1, len1 + 1):
            curr[0] = i
            for j in range(1, len2 + 1):
                cost = 0 if cs1[i - 1] == cs2[j - 1] else 1

                tmp = prev[j] + 1
                if curr[j - 1] + 1 < tmp:
                    tmp = curr[j - 1] + 1
                if prev[j - 1] + cost < tmp:
                    tmp = prev[j - 1] + cost

                curr[j] = tmp

            tmp_ptr = prev
            prev = curr
            curr = tmp_ptr

    tmp = prev[len2]
    free(prev)
    free(curr)
    return tmp

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

    cdef float score = max2float(part * 0.75, full * 0.6)

    if s1 and s2 and s1[0] != s2[0]:
        score -= 0.1

    cdef int len_diff = abs(len(s1) - len(s2))
    if len_diff >= 1:
        score -= 0.035 * len_diff / max_len

    cdef int common_prefix_len = 0
    cdef int min_len = min(len(s1), len(s2))
    for i in range(min_len):
        if s1[i] == s2[i]:
            common_prefix_len += 1
        else:
            break
    score += 0.02 * common_prefix_len

    if score > 1.0:
        score = 1.0
    elif score < 0.0:
        score = 0.0

    return score


cpdef float compute_text_match_score(str s1, str s2):
    if not s1 and not s2:
        return 1.0

    if s1 == s2:
        return 1.0

    s1 = s1.strip().lower()
    s2 = s2.strip().lower()

    cdef int len1 = len(s1)
    cdef int len2 = len(s2)

    if len1 == 0 or len2 == 0:
        return 0.0

    cdef int dist = levenshtein_distance(s1, s2)
    cdef float max_len = max2(len1, len2)

    cdef float full = 1.0 - (dist / max_len)

    cdef float part = 0.0
    if len1 < len2:
        part = partial_ratio(s1, s2)
    elif len2 < len1:
        part = partial_ratio(s2, s1)

    cdef float score
    if abs(len1 - len2) < 5:
        score = 0.7 * full + 0.3 * part
    else:
        score = 0.4 * full + 0.6 * part

    if s1 in s2 or s2 in s1:
        score += 0.15

    cdef int len_diff = abs(len1 - len2)
    score -= 0.1 * (len_diff / max_len)

    cdef int common_prefix_len = 0
    cdef int min_len = min(len1, len2)
    for i in range(min_len):
        if s1[i] == s2[i]:
            common_prefix_len += 1
        else:
            break

    score += 0.015 * common_prefix_len

    if score > 1.0:
        score = 1.0
    elif score < 0.0:
        score = 0.0

    return score


cpdef float token_set_ratio(str s1, str s2):
    s1 = s1.lower().replace("(", " ").replace(")", " ").replace(",", " ")
    s2 = s2.lower().replace("(", " ").replace(")", " ").replace(",", " ")

    cdef set tokens1 = set(s1.split())
    cdef set tokens2 = set(s2.split())

    if not tokens1 or not tokens2:
        return 0.0

    cdef int common = len(tokens1.intersection(tokens2))
    cdef int total = len(tokens1) + len(tokens2) - common

    cdef float score = common / total

    cdef int extra = abs(len(tokens1) - len(tokens2))
    score -= 0.02 * extra

    if score < 0.0:
        score = 0.0

    return score
