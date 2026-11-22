"""Fixed specifications and deterministic independent reference implementations."""

import itertools


PROMPTS = {
    "s-last": "Return a list retaining only the LAST occurrence of each integer in xs, preserving the positions of those retained occurrences. Example [2,1,2,3,1] -> [2,3,1].",
    "s-climb": "Return the length of the longest contiguous strictly increasing run of integers in xs. Equal neighbors break a run. Empty list -> 0. Example [3,1,2,2,3,4] -> 3.",
    "t-frequency": "Return the distinct integers in xs, ordered by decreasing occurrence count. Break ties by the position of the LAST occurrence, EARLIEST last occurrence first. Empty list -> [].",
    "t-minima": "Return, in ascending order, the indices i such that xs[i] is strictly smaller than EVERY element to its right. The last index always qualifies if there is one. Equal values matter. Empty list -> [].",
    "h-mode": "Return the most frequent integer in xs. Among tied values choose the one with the LARGEST distance between its first and last indices. If still tied choose the one whose first occurrence is EARLIEST. Empty list -> None.",
    "h-descent": "Return the number of MAXIMAL contiguous strictly decreasing runs in xs that have length at least k, where k is 2, 3, or 4. Equal neighbors break a run. Count a qualifying run only once regardless of length. Example xs=[4,3,2,1,1,0], k=2 -> 2.",
}


def reference(task, xs, k):
    positions = {}
    for i, x in enumerate(xs):
        positions.setdefault(x, []).append(i)
    if task == "s-last":
        return sorted(positions, key=lambda x: positions[x][-1])
    if task == "t-frequency":
        return sorted(positions, key=lambda x: (-len(positions[x]), positions[x][-1]))
    if task == "h-mode":
        return max(positions, default=None, key=lambda x: (
            len(positions[x]), positions[x][-1]-positions[x][0], -positions[x][0]))
    if task == "t-minima":
        chosen = []
        smallest = None
        for i in range(len(xs)-1, -1, -1):
            if smallest is None or xs[i] < smallest:
                chosen.append(i)
                smallest = xs[i]
        return list(reversed(chosen))
    if task not in {"s-climb", "h-descent"}:
        raise KeyError(task)
    lengths = []
    for i, x in enumerate(xs):
        continues = i and (x > xs[i-1] if task == "s-climb" else x < xs[i-1])
        if continues:
            lengths[-1] += 1
        else:
            lengths.append(1)
    return max(lengths, default=0) if task == "s-climb" else sum(n >= k for n in lengths)


def cases(task):
    # Exhaust short inputs; longer examples exercise distant ties and long runs.
    inputs = [list(x) for n in range(5) for x in itertools.product((-1, 0, 2), repeat=n)]
    inputs += [[4,3,2,1,1,0], [2,1,2,3,1], [2,1,1,2,3,3], [3,1,2,2,3,4],
               [8,7,6,5,4,3,2,1], [2,1,0,3,2,1,0], [0,3,1,2,1,3,2],
               [3,2,1,3,2,1], [10,-5,10,0,-5,0], [3,2,3,1,2,1,1,0]]
    return [(xs, k, reference(task, xs, k)) for xs in inputs
            for k in ((2,3,4) if task == "h-descent" else (2,))]
