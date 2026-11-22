"""Local paired programming experiment. Run with Python 3.10+ from any directory."""
import csv
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from paired_analysis import analyze
from tasks import PROMPTS, cases


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
P = json.loads((ROOT / "protocol.json").read_text(encoding="utf-8"))
GRADER = (ROOT / "grade_expression.py").read_text(encoding="utf-8")
MODEL = P["model"]
LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))
DB = None
IMAGE = None


def encode(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(obj):
    return hashlib.sha256(encode(obj).encode()).hexdigest()


def seed(*parts):
    return int(digest([P["seed_namespace"], *parts])[:8], 16) & 0x7fffffff


def ollama(path, payload=None):
    req = urllib.request.Request("http://127.0.0.1:11434/api/" + path,
        data=None if payload is None else encode(payload).encode(),
        headers={"Content-Type": "application/json"})
    with LOCAL.open(req, timeout=360) as resp:
        return json.load(resp)


def event(key, inputs, produce):
    fingerprint = digest(inputs)
    previous = DB.execute("SELECT hash, output FROM event WHERE id=?", (key,)).fetchone()
    if previous:
        if previous[0] != fingerprint:
            raise RuntimeError("Cannot reuse changed experiment input: " + key)
        return json.loads(previous[1])
    result = produce()
    with DB:
        DB.execute("INSERT INTO event VALUES (?,?,?,?,?,?)",
                   (key, fingerprint, encode(inputs), encode(result), time.time(), MODEL))
    return result


def generate(key, prompt, sampling_seed, limit, temp, schema=None):
    payload = {"model": MODEL, "stream": False, "think": False, "keep_alive": "30m",
               "messages": [{"role": "user", "content": prompt}], "options": {
                   "temperature": temp, "seed": sampling_seed, "num_ctx": 8192,
                   "num_predict": limit}}
    if schema:
        payload["format"] = schema
    result = event(key, payload, lambda: ollama("chat", payload))
    return result["message"]["content"].strip()


def structured(key, prompt, sampling_seed, schema, limit):
    for attempt in range(3):
        raw = generate(f"{key}/sample{attempt}", prompt, sampling_seed,
                       limit * (attempt+1), P["temperature_optimizer"], schema)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            continue
    raise RuntimeError("Optimizer returned incomplete JSON three times: " + key)


def check_program(expression, task):
    tests = cases(task)
    inputs = {"expression": expression, "cases": tests}
    def run():
        name = "sim-grade-" + os.urandom(8).hex()
        cmd = ["docker", "run", "--name", name, "--rm", "-i", "--network", "none",
               "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges",
               "--user", "65534:65534", "--memory=128m", "--memory-swap=128m",
               "--cpus=1", "--pids-limit=16", IMAGE, "python", "-IB", "-c", GRADER]
        try:
            proc = subprocess.run(cmd, input=encode(inputs), capture_output=True,
                                  encoding="utf-8", timeout=25)
        except subprocess.TimeoutExpired:
            # Distinguish a running, timed-out grader from a daemon/startup failure.
            live = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", name],
                                  capture_output=True, text=True)
            if live.stdout.strip() != "true":
                raise RuntimeError("Container failed to start or respond")
            subprocess.run(["docker", "rm", "-f", name], check=True, capture_output=True)
            return {"passed": 0, "correct": 0, "total": len(tests), "example": "Time limit"}
        if proc.returncode == 137:
            return {"passed": 0, "correct": 0, "total": len(tests), "example": "Memory limit"}
        if proc.returncode:
            raise RuntimeError("Grader infrastructure failure: " + proc.stderr[-1000:])
        return json.loads(proc.stdout)
    # Only deterministic test execution is reused. Every rollout has its own model request.
    return event("grade/" + digest([task, expression]), inputs, run)


SOLVER = ("Write a Python 3.12 expression only. No assignment, imports, Markdown or explanation. "
          "Inputs: xs (list of integers) and k (integer, used only if specified). "
          "Comprehensions, lambda and slicing are allowed. Available functions: abs all any bool "
          "dict enumerate filter int len list map max min next range reversed set sorted sum tuple "
          "zip groupby pairwise. Available methods: count index get items keys values fromkeys.\n")


def solve(prefix, task, guide, sampling_seed):
    raw = generate(prefix + "/answer", SOLVER + "General work instructions: " + guide
                   + "\nTask: " + PROMPTS[task], sampling_seed, 160, P["temperature_solver"])
    fence = re.fullmatch(r"```(?:python)?\s*\n(.*?)\n?```", raw, flags=re.S|re.I)
    program = fence.group(1).strip() if fence else raw
    return {"task": task, "program": program, **check_program(program, task)}


def development(prefix, tasks, guide, seed_parts):
    return [solve(f"{prefix}/{task}", task, guide, seed(*seed_parts, task)) for task in tasks]


TEXT = {"type": "string"}
FIELDS = {"problem": TEXT, "guide": TEXT, "reason": TEXT,
          "predicted": {"type": "array", "items": TEXT}}
ITEM = {"type":"object", "properties":FIELDS, "required":list(FIELDS),
        "additionalProperties":False}
PROPOSALS = {"type":"object","properties":{"choices":{"type":"array","minItems":2,
             "maxItems":2,"items":ITEM}},"required":["choices"],"additionalProperties":False}
SELECTION = {"type":"object","properties":{"choice":{"type":"integer","enum":[0,1,2]}},
             "required":["choice"],"additionalProperties":False}


def stage(pair, arm, guide, source_memory):
    phase = "source" if arm == "source" else "target"
    tasks = P[phase]["evolve"]
    prefix = f"pair{pair:02d}/{arm}"
    memory = list(source_memory)
    history = []
    evidence = development(prefix+"/base", tasks, guide, (pair, phase, "baseline"))
    for n in range(1, P["rounds_per_stage"] + 1):
        round_id = f"{prefix}/round{n}"
        context = {"working_guide": guide, "development_evidence": evidence,
                   "ordinary_history": history}
        if arm != "no_sim":
            context["self_improvement_memory"] = memory
        prompt = ("You improve a reusable guide for a separate Python programmer. "
                  "Propose two DIFFERENT concise replacement guides (max 24 words each), "
                  "describing general work habits usable on new coding tasks. "
                  "Keep both free of task IDs, task-specific answers and code. For each "
                  "give a short recurring problem name (reuse an existing name when it fits), "
                  "one short reason and predicted task IDs fixed (possibly empty). "
                  "The solver will see only the guide.\n" + encode(context))
        proposed = structured(round_id+"/propose", prompt, seed(pair,phase,n,"proposer"),
                              PROPOSALS, 320)["choices"]
        if len(proposed) != 2 or any(not c["guide"].strip() for c in proposed):
            raise ValueError("Invalid proposer output at " + round_id)
        evaluations = [development(f"{round_id}/edit{j}", tasks, choice["guide"],
                                   (pair,phase,n,"dev")) for j,choice in enumerate(proposed, 1)]
        choices = [{"choice":0,"guide":guide,"feedback":evidence}] + [
            {"choice":i+1, "proposal":c, "feedback":evaluations[i]}
            for i,c in enumerate(proposed)]
        prompt = ("Select the guide to retain for new programming tasks. Choose 0 (keep), "
                  "1 or 2. Consider actual passes, partial correctness, generality and "
                  "risk of regression. Prefer a useful tested revision when scores tie and "
                  "it clearly improves the guidance.\n" + encode({"context":context,"choices":choices}))
        picked = structured(round_id+"/select", prompt, seed(pair,phase,n,"selector"),
                            SELECTION, 20)["choice"]
        previous = evidence
        history.append({"round":n, "previous_guide":guide, "candidates":proposed,
                        "measured":evaluations, "choice":picked})
        if picked:
            choice, evidence = proposed[picked-1], evaluations[picked-1]
            guide = choice["guide"]
            if arm != "no_sim":
                record = {"stage":phase,"round":n,"model":MODEL, **choice,
                          "before":{e["task"]:e["passed"] for e in previous},
                          "observed":{e["task"]:{"passed":e["passed"],"correct":e["correct"],
                                      "total":e["total"]} for e in evidence}}
                # Store attempts together under the exact recurring problem.
                memory = json.loads(encode(memory))
                entry = next((e for e in memory if e["problem"] == choice["problem"]), None)
                if entry is None:
                    entry = {"problem":choice["problem"],"attempts":[]}
                    memory.append(entry)
                entry["attempts"].append(record)
        state = {"guide":guide,"memory":memory,"pair":pair,"arm":arm,"round":n}
        event(round_id+"/retained", state, lambda: state)
    return state


def main():
    global DB, IMAGE
    OUT.mkdir(exist_ok=True)
    tags = ollama("tags")["models"]
    if not any(t["name"] == MODEL and t["digest"] == P["model_digest"] for t in tags):
        raise RuntimeError("The local model does not match the registered digest.")
    IMAGE = subprocess.check_output(["docker","image","inspect","python:3.12-slim",
                                    "--format","{{.Id}}"], text=True).strip()
    DB = sqlite3.connect(OUT / "observations.sqlite")
    DB.execute("CREATE TABLE IF NOT EXISTS event (id TEXT PRIMARY KEY, hash TEXT, inputs TEXT, "
               "output TEXT, recorded_at REAL, model TEXT)")
    manifest = {"protocol":P,"grader_image":IMAGE,"files":{
        name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
        for name in ("tasks.py","grade_expression.py","run_pairs.py","paired_analysis.py")}}
    event("registered", manifest, lambda: manifest)
    final_rows = []
    for pair in range(1, P["pairs"]+1):
        source = stage(pair,"source",P["initial_guide"],[])
        print(f"Pair {pair}: source checkpoint ready", flush=True)
        arms = ["sim","no_sim"] if pair%2 else ["no_sim","sim"]
        endpoints = {}
        for arm in arms:
            endpoints[arm] = stage(pair, arm, source["guide"], source["memory"] if arm=="sim" else [])
            print(f"Pair {pair}: {arm} optimization complete", flush=True)
        # Held-out data is first accessed after BOTH endpoints have been committed.
        for label in ["start", *arms]:
            chosen = source if label == "start" else endpoints[label]
            for task in P["target"]["held_out"]:
                for attempt in range(1,P["held_out_attempts"]+1):
                    key = f"pair{pair:02d}/final/{label}/{task}/{attempt}"
                    check = solve(key,task,chosen["guide"],seed(pair,"held_out",task,attempt))
                    row = dict(pair=pair, arm=label, task=task, attempt=attempt,
                               passed=str(check["passed"]), source_snapshot_sha256=digest(source))
                    event(key+"/trial",row,lambda:row)
                    if label != "start":
                        final_rows.append(row)
        print(f"Pair {pair}: held-out evaluation complete", flush=True)
    with (OUT/"final_trials.csv").open("w",newline="",encoding="utf-8") as stream:
        writer = csv.DictWriter(stream,fieldnames=final_rows[0])
        writer.writeheader()
        writer.writerows(final_rows)
    summary = analyze(P,final_rows)
    (OUT/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(encode(summary),flush=True)


if __name__ == "__main__":
    main()
