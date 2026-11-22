"""Check the primary result against the recorded optimizer and solver calls."""
import csv
import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
from pathlib import Path

from paired_analysis import analyze
from tasks import PROMPTS, cases


def audit(regrade=False):
    root = Path(__file__).resolve().parent
    out = root / "results"
    with sqlite3.connect((out / "observations.sqlite").as_uri() + "?mode=ro", uri=True) as db:
        events = {k: (json.loads(i), json.loads(o), at) for k, i, o, at in
                  db.execute("SELECT id,inputs,output,recorded_at FROM event")}
    registered = events["registered"][1]
    protocol = registered["protocol"]
    if protocol != json.loads((root / "protocol.json").read_text(encoding="utf-8")):
        raise ValueError("Registered protocol differs from disk")
    for name, sha in registered["files"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != sha:
            raise ValueError("Registered file changed: " + name)

    def digest(obj):
        return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                         separators=(",", ":")).encode()).hexdigest()

    def answers(key):
        request, response, _ = events[key]
        if request["model"] != protocol["model"] or response["model"] != protocol["model"]:
            raise ValueError("Wrong model for " + key)
        return request["options"]["seed"]

    verified = []
    starts = []
    regrade_inputs = []
    original_grades = []
    source_seeds = set()
    for pair in range(1, 11):
        p = f"pair{pair:02d}"
        last = protocol["rounds_per_stage"]
        source = events[f"{p}/source/round{last}/retained"][1]
        for arm in ("source","no_sim","sim"):
            phase = "source" if arm == "source" else "target"
            for task in protocol[phase]["evolve"]:
                answers(f"{p}/{arm}/base/{task}/answer")
            if arm == "source":
                initial = protocol["source"]["evolve"][0]
                source_seeds.add(answers(f"{p}/source/base/{initial}/answer"))
            for n in range(1,last+1):
                rid = f"{p}/{arm}/round{n}"
                for role in ("propose","select"):
                    request = events[rid + "/" + role + "/sample0"][0]
                    prompt = request["messages"][0]["content"]
                    context = json.loads(prompt.split("\n",1)[1])
                    if role == "select":
                        context = context["context"]
                    if arm == "no_sim" and "self_improvement_memory" in context:
                        raise ValueError("Control saw SIM")
                    if arm in ("no_sim","sim") and n == 1:
                        if context["working_guide"] != source["guide"]:
                            raise ValueError("Mismatched initial guide")
                        if arm == "sim" and context["self_improvement_memory"] != source["memory"]:
                            raise ValueError("SIM did not inherit its source record")
                    if any(task in prompt or PROMPTS[task] in prompt
                           for task in protocol["target"]["held_out"]):
                        raise ValueError("Held-out task ID in optimizer input")
                for edit in range(1, protocol["proposals_per_round"]+1):
                    for task in protocol[phase]["evolve"]:
                        k = f"{rid}/edit{edit}/{task}/answer"
                        s = answers(k)
                        if arm == "sim" and s != answers(k.replace("/sim/","/no_sim/")):
                            raise ValueError("Different paired development seeds")
                events[rid + "/retained"]
        for task in protocol["target"]["held_out"]:
            for attempt in range(1,6):
                matched = []
                for arm in ("start","no_sim","sim"):
                    key = f"{p}/final/{arm}/{task}/{attempt}"
                    matched.append(answers(key+"/answer"))
                    for endpoint in ("sim","no_sim"):
                        if events[key+"/answer"][2] < events[f"{p}/{endpoint}/round{last}/retained"][2]:
                            raise ValueError("Held-out answer preceded final selection")
                    row = events[key+"/trial"][1]
                    raw = events[key+"/answer"][1]["message"]["content"].strip()
                    fence = re.fullmatch(r"```(?:python)?\s*\n(.*?)\n?```", raw, flags=re.S|re.I)
                    program = fence[1].strip() if fence else raw
                    checked = events["grade/"+digest([task,program])][1]
                    if checked["passed"] != int(row["passed"]):
                        raise ValueError("Trial differs from the grader record")
                    if regrade:
                        regrade_inputs.append(json.dumps({"expression":program, "cases":cases(task)}))
                        original_grades.append(checked)
                    if row["source_snapshot_sha256"] != digest(source):
                        raise ValueError("Held-out trial not linked to its source checkpoint")
                    recorder = starts if arm == "start" else verified
                    recorder.append(row)
                if len(set(matched)) != 1:
                    raise ValueError("Different paired held-out seeds")
    if len(source_seeds) != 10:
        raise ValueError("Source runs did not use ten independent seeds")
    with (out / "final_trials.csv").open(encoding="utf-8", newline="") as stream:
        csv_rows = list(csv.DictReader(stream))
    normalized = lambda rows: sorted(tuple(sorted((k, str(v)) for k,v in r.items())) for r in rows)
    if normalized(verified) != normalized(csv_rows):
        raise ValueError("Final CSV differs from recorded trials")
    summary = analyze(protocol, verified)
    if summary != json.loads((out/"summary.json").read_text(encoding="utf-8")):
        raise ValueError("Summary differs from independently reconstructed trial table")
    if regrade:
        grader = (root/"grade_expression.py").read_text(encoding="utf-8").split(
            'if __name__ == "__main__":')[0]
        grader += '\nfor line in sys.stdin:\n    print(json.dumps(grade(json.loads(line))))\n'
        run = subprocess.run(["docker","run","--rm","-i","--network","none","--read-only",
                              "--cap-drop=ALL","--security-opt=no-new-privileges",
                              "--user","65534:65534","--memory=128m","--memory-swap=128m",
                              "--cpus=1","--pids-limit=16",registered["grader_image"],
                              "python","-IB","-c",grader],
                             input="\n".join(regrade_inputs)+"\n", capture_output=True,
                             encoding="utf-8", timeout=240, check=True)
        replay = [json.loads(line) for line in run.stdout.splitlines()]
        # Diagnostic reprs of invalid objects can contain process-local addresses.
        scores = lambda rows: [(g["passed"],g["correct"],g["total"]) for g in rows]
        if scores(replay) != scores(original_grades):
            raise ValueError("Fresh container grading differs from recorded scores")
    return {"checked_source_runs":10,"checked_optimization_rounds":60,
            "checked_target_final_trials":len(verified),"checked_start_trials":len(starts),
            "regraded_trials":len(regrade_inputs),
            "mean_start_score":100*sum(int(r["passed"]) for r in starts)/len(starts),
            "summary":summary}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regrade",action="store_true")
    print(json.dumps(audit(parser.parse_args().regrade),indent=2))
