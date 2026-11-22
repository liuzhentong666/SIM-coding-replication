"""Analyze final held-out trials from ten independent paired continuations."""

import argparse
import csv
import itertools
import json
import math
import statistics
from pathlib import Path


def paired_summary(differences):
    if len(differences) != 10:
        raise ValueError("The protocol requires exactly ten independent source runs.")
    mean = statistics.mean(differences)
    error = statistics.stdev(differences) / math.sqrt(10)
    # Two-sided 95% paired t interval with nine degrees of freedom.
    margin = 2.2621571628540993 * error
    nonzero = [x for x in differences if x != 0]
    sizes = sorted(abs(x) for x in nonzero)
    # Twice the average rank avoids floating-point ties in sign enumeration.
    twice_rank = [sum(i for i, z in enumerate(sizes, 1) if z == abs(x)) * 2
                  // sizes.count(abs(x)) for x in nonzero]
    observed = abs(sum(r if x > 0 else -r for x, r in zip(nonzero, twice_rank)))
    ranksums = (abs(sum(s * r for s, r in zip(signs, twice_rank)))
                for signs in itertools.product((-1, 1), repeat=len(nonzero)))
    return {
        "pairs": 10, "wins": sum(x > 0 for x in differences),
        "ties": differences.count(0), "losses": sum(x < 0 for x in differences),
        "mean_gain_points": mean, "paired_t_95ci_points": [mean-margin, mean+margin],
        "exact_signed_rank_p": sum(z >= observed for z in ranksums) / (2**len(nonzero)),
    }


def analyze(protocol, rows):
    tasks = protocol["target"]["held_out"]
    if not tasks or len(tasks) != len(set(tasks)):
        raise ValueError("Held-out task IDs must be nonempty and unique.")
    if set(tasks) & set(protocol["target"]["evolve"]):
        raise ValueError("Held-out tasks also appear in the optimization set.")
    arms = ("no_sim", "sim")
    expected = set(itertools.product(range(1, 11), arms, tasks, range(1, 6)))
    scores = {}
    checkpoints = {}
    for row in rows:
        pair = int(row["pair"])
        key = pair, row["arm"], row["task"], int(row["attempt"])
        if key not in expected or key in scores:
            raise ValueError(f"Unexpected or duplicate final trial: {key}")
        start = row["source_snapshot_sha256"]
        if len(start) != 64 or any(c not in "0123456789abcdef" for c in start):
            raise ValueError(f"Invalid source snapshot digest for pair {pair}")
        if checkpoints.setdefault(pair, start) != start:
            raise ValueError(f"Branches of pair {pair} have different source snapshots.")
        if row["passed"] not in ("0", "1"):
            raise ValueError(f"Expected a binary verifier result for {key}")
        scores[key] = int(row["passed"])
    if expected != scores.keys():
        raise ValueError(f"Missing {len(expected - scores.keys())} required final trials.")
    denominator = 5 * len(tasks)
    pairs = []
    differences = []
    for pair in range(1, 11):
        counts = {arm: sum(scores[pair, arm, task, n] for task in tasks for n in range(1, 6))
                  for arm in arms}
        delta = 100 * (counts["sim"] - counts["no_sim"]) / denominator
        pairs.append(dict(pair=pair, trials_per_arm=denominator, **counts, gain_points=delta))
        differences.append(delta)
    return {"per_pair": pairs, **paired_summary(differences)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("protocol", type=Path)
    parser.add_argument("final_trials", type=Path)
    args = parser.parse_args()
    with args.final_trials.open(encoding="utf-8-sig", newline="") as stream:
        print(json.dumps(analyze(json.loads(args.protocol.read_text(encoding="utf-8")),
                                 csv.DictReader(stream)), indent=2, allow_nan=False))
