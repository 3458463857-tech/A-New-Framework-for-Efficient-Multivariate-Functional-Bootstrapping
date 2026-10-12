"""Frozen integer semantics for the ten-function comparison; no FHE code."""
from collections import Counter

TASKS = {
    "lower_median3_6": (3, 6),
    "mode3_6": (3, 6),
    "set_interval4_6": (4, 6),
    "set_threshold4_6": (4, 6),
    "hamming_interval10": (2, 10),
    "max3_6": (3, 6),
    "range3_6": (3, 6),
    "iqr3_6": (3, 6),
    "mad3_6": (3, 6),
    "distinct3_6": (3, 6),
}

def target(task_id, values):
    t, n = TASKS[task_id]
    assert len(values) == n and all(isinstance(x, int) and 0 <= x < t for x in values)
    s = sorted(values)
    if task_id == "lower_median3_6":
        return s[(n - 1) // 2]
    if task_id == "mode3_6":
        counts = Counter(values)
        return min(x for x, c in counts.items() if c == max(counts.values()))
    if task_id == "set_interval4_6":
        return int(2 <= sum(x in (1, 3) for x in values) <= 4)
    if task_id == "set_threshold4_6":
        return int(sum(x in (0, 2) for x in values) >= 3)
    if task_id == "hamming_interval10":
        return int(4 <= sum(values) <= 6)
    if task_id == "max3_6":
        return s[-1]
    if task_id == "range3_6":
        return s[-1] - s[0]
    if task_id == "iqr3_6":
        return s[3 * (n - 1) // 4] - s[(n - 1) // 4]
    if task_id == "mad3_6":
        center = s[(n - 1) // 2]
        return sorted(abs(x - center) for x in values)[(n - 1) // 2]
    if task_id == "distinct3_6":
        return len(set(values))
    raise KeyError(task_id)

def score(task_id, values):
    if task_id == "hamming_interval10":
        return sum(values)
    if task_id == "set_interval4_6":
        return sum(x in (1, 3) for x in values)
    if task_id == "set_threshold4_6":
        return sum(x in (0, 2) for x in values)
    return sum((7, 0, 5)[x] for x in values)
