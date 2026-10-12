"""Frozen small-domain instances of the same seven ternary statistics."""
from collections import Counter
TASKS = {
    "lower_median3_3": (3,3), "mode3_4": (3,4), "max3_3": (3,3),
    "range3_3": (3,3), "iqr3_4": (3,4), "mad3_3": (3,3), "distinct3_3": (3,3),
}
def target(task_id, values):
    t,n=TASKS[task_id]
    assert len(values)==n and all(isinstance(x,int) and 0<=x<t for x in values)
    s=sorted(values)
    if task_id.startswith('lower_median'):return s[(n-1)//2]
    if task_id.startswith('mode'):
        c=Counter(values);return min(x for x,v in c.items() if v==max(c.values()))
    if task_id.startswith('max'):return s[-1]
    if task_id.startswith('range'):return s[-1]-s[0]
    if task_id.startswith('iqr'):return s[3*(n-1)//4]-s[(n-1)//4]
    if task_id.startswith('mad'):return sorted(abs(x-s[(n-1)//2]) for x in values)[(n-1)//2]
    if task_id.startswith('distinct'):return len(set(values))
    raise KeyError(task_id)
def score(task_id, values):
    _,n=TASKS[task_id]
    return sum((n+1,0,n)[x] for x in values)
