"""Rescore the two final branches with the single-name '_' exception."""
import ast
import csv
import hashlib
import json
import re
import sqlite3
import subprocess
from collections import Counter
from contextlib import closing
from pathlib import Path

from audit_results import audit
from paired_analysis import analyze
from tasks import cases


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
ORIGINAL_RULE = 'isinstance(node, ast.Name) and node.id.startswith("_")'
REVISED_RULE = 'isinstance(node, ast.Name) and node.id != "_" and node.id.startswith("_")'
REPLAY = """
requests = json.load(sys.stdin)
for request in requests:
    print(json.dumps(grade(request)))
"""


def score_saved_answers(image, grader, requests):
    worker = grader.split('if __name__ == "__main__":', 1)[0] + REPLAY
    run = subprocess.run(
        ["docker", "run", "--rm", "-i", "--network", "none", "--read-only",
         "--cap-drop=ALL", "--security-opt=no-new-privileges", "--user", "65534:65534",
         "--memory=128m", "--memory-swap=128m", "--cpus=1", "--pids-limit=16",
         image, "python", "-IB", "-c", worker],
        input=json.dumps(requests), capture_output=True, encoding="utf-8",
        timeout=240, check=True,
    )
    grades = [json.loads(line) for line in run.stdout.splitlines()]
    if len(grades) != len(requests):
        raise ValueError("The scorer did not return one grade for every answer")
    return grades


def main():
    audit()
    grader = (ROOT / "grade_expression.py").read_text(encoding="utf-8")
    if grader.count(ORIGINAL_RULE) != 1:
        raise ValueError("Expected exactly one original name rule")
    corrected = grader.replace(ORIGINAL_RULE, REVISED_RULE)
    ast.parse(corrected)

    with closing(sqlite3.connect((RESULTS / "observations.sqlite").as_uri() + "?mode=ro",
                                 uri=True)) as db:
        events = {key: json.loads(output)
                  for key, output in db.execute("SELECT id, output FROM event")}
    registration = events["registered"]
    protocol = registration["protocol"]
    with (RESULTS / "final_trials.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    test_cases = {task: cases(task) for task in protocol["target"]["held_out"]}

    requests = []
    for row in rows:
        task = row["task"]
        key = f"pair{int(row['pair']):02d}/final/{row['arm']}/{task}/{row['attempt']}"
        text = events[key + "/answer"]["message"]["content"].strip()
        fence = re.fullmatch(r"```(?:python)?\s*\n(.*?)\n?```", text, flags=re.S | re.I)
        expression = fence[1].strip() if fence else text
        requests.append({"expression": expression, "cases": test_cases[task]})

    image = registration["grader_image"]
    probes = [{"expression": f"len([0 for {name} in xs])", "cases": [([42], 0, 1)]}
              for name in ("_", "_hidden", "__hidden")]
    originals = score_saved_answers(image, grader, requests)
    new_grades = score_saved_answers(image, corrected, probes + requests)
    if [r["passed"] for r in new_grades[:len(probes)]] != [1, 0, 0]:
        raise ValueError("The revised rule did not allow only the intended placeholder")

    task_totals = Counter()
    improved = Counter()
    for row, old, new in zip(rows, originals, new_grades[len(probes):]):
        original = int(row["passed"])
        if old["passed"] != original or (old["total"] != new["total"]):
            raise ValueError(f"Original results or test cases do not match saved trial: {row}")
        if new["passed"] < original:
            raise ValueError(f"Allowing an extra name unexpectedly invalidated a passing answer: {row}")
        row["original_passed"] = row["passed"]
        row["passed"] = str(new["passed"])
        key = row["task"], row["arm"]
        task_totals[key] += new["passed"]
        improved[key] += new["passed"] - original

    summary = analyze(protocol, rows)
    arms = ("sim", "no_sim")
    tasks = protocol["target"]["held_out"]
    attempts = protocol["pairs"] * protocol["held_out_attempts"]
    summary["regrade"] = {
        "rule": REVISED_RULE,
        "grader_image": image,
        "original_grader_sha256": registration["files"]["grade_expression.py"],
        "revised_grader_sha256": hashlib.sha256(corrected.encode("utf-8")).hexdigest(),
        "replayed_original_trials": len(originals),
        "per_task": [
            {
                "task": task,
                "trials_per_arm": attempts,
                **{arm: task_totals[task, arm] for arm in arms},
                "gained_passes": {arm: improved[task, arm] for arm in arms},
            } for task in tasks
        ],
        "totals": {
            arm: {
                "trials": attempts * len(tasks),
                "passed": sum(task_totals[task, arm] for task in tasks),
                "gained_passes": sum(improved[task, arm] for task in tasks),
            } for arm in arms
        },
    }

    out = RESULTS / "regrade-allow-underscore"
    out.mkdir(exist_ok=True)
    with (out / "final_trials.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
