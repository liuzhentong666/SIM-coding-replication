"""Fixed specifications and deterministic independent reference implementations."""

import itertools


PROMPTS = {
    "h-prefix": "Return the running sums of xs as a list, in order. Example [2,-3,4] -> [2,-1,3]. Empty input -> [].",
    "h-changes": "Return in ascending order the indices i greater than zero where xs[i] differs from its immediate predecessor. Example [2,2,1,3] -> [2,3].",
    "h-nearest": "For each element return the distance to its nearest equal element strictly to the left, or 0 if none. Example [1,3,1,1] -> [0,0,2,1].",
    "h-window": "Return a list of the maximum of each contiguous length-k window of xs in left-to-right order. Return [] if no complete window exists.",
    "h-evenruns": "Return the lengths, in order, of all maximal consecutive blocks of even integers in xs. Example [2,4,1,0,3] -> [2,1].",
    "h-balance": "Return the earliest index i for which the sum strictly to its left equals the sum strictly to its right. Return -1 if none. Example [1,5,1] -> 1.",
    "h-single": "Return all integers occurring exactly once in xs, in their original order. Example [4,1,4,0] -> [1,0].",
    "h-separation": "Count pairs of indices i < j with xs[i] == xs[j] and j-i >= k. Count every qualifying pair. Example xs=[3,3,3,3], k=2 -> 3.",
    "s-last": "Return a list retaining only the LAST occurrence of each integer in xs, preserving the positions of those retained occurrences. Example [2,1,2,3,1] -> [2,3,1].",
    "s-climb": "Return the length of the longest contiguous strictly increasing run of integers in xs. Equal neighbors break a run. Empty list -> 0. Example [3,1,2,2,3,4] -> 3.",
    "t-frequency": "Return the distinct integers in xs, ordered by decreasing occurrence count. Break ties by the position of the LAST occurrence, EARLIEST last occurrence first. Empty list -> [].",
    "t-minima": "Return, in ascending order, the indices i such that xs[i] is strictly smaller than EVERY element to its right. The last index always qualifies if there is one. Equal values matter. Empty list -> [].",
    "h-mode": "Return the most frequent integer in xs. Among tied values choose the one with the LARGEST distance between its first and last indices. If still tied choose the one whose first occurrence is EARLIEST. Empty list -> None.",
    "h-descent": "Return the number of MAXIMAL contiguous strictly decreasing runs in xs that have length at least k, where k is 2, 3, or 4. Equal neighbors break a run. Count a qualifying run only once regardless of length. Example xs=[4,3,2,1,1,0], k=2 -> 2.",
}


def reference(task, xs, k):
    if task == "h-prefix":
        return list(itertools.accumulate(xs))
    if task == "h-changes":
        return [i for i in range(1, len(xs)) if xs[i] != xs[i - 1]]
    if task == "h-nearest":
        last = {}
        distances = []
        for i, x in enumerate(xs):
            distances.append(i - last.get(x, i))
            last[x] = i
        return distances
    if task == "h-window":
        return [max(xs[i:i + k]) for i in range(len(xs) - k + 1)]
    if task == "h-evenruns":
        return [len(list(group)) for odd, group in itertools.groupby(xs, key=lambda x: x % 2) if not odd]
    if task == "h-balance":
        right = sum(xs)
        left = 0
        for i, x in enumerate(xs):
            right -= x
            if left == right:
                return i
            left += x
        return -1
    if task == "h-single":
        return [x for x in xs if xs.count(x) == 1]
    if task == "h-separation":
        return sum(xs[i] == xs[j] for i, j in itertools.combinations(range(len(xs)), 2) if j - i >= k)
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
            for k in ((2,3,4) if task in {"h-descent", "h-window", "h-separation"} else (2,))]
