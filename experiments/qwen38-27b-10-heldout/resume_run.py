"""Resume the registered run, retrying interrupted local inference requests."""
import http.client
import json
import time
import urllib.error

import run_pairs
from audit_results import audit


open_once = run_pairs.LOCAL.open
grade_once = run_pairs.check_program


def grade_with_retry(expression, task):
    for attempt in range(4):
        try:
            return grade_once(expression, task)
        except RuntimeError as exc:
            transient = str(exc).startswith(("Grader infrastructure failure:", "Container failed to start or respond"))
            if not transient or attempt == 3:
                raise
            print(f"Scoring service interrupted for {task}, retrying saved answer", flush=True)
            time.sleep(15 * (attempt + 1))


def open_local(request, timeout):
    for attempt in range(4):
        try:
            return open_once(request, timeout=max(timeout, 900))
        except (TimeoutError, ConnectionError, http.client.RemoteDisconnected,
                urllib.error.URLError) as exc:
            if isinstance(exc, urllib.error.HTTPError) and exc.code < 500:
                raise
            if attempt == 3:
                raise
            print(f"Local request interrupted, retrying: {exc}", flush=True)
            time.sleep(15)


if __name__ == "__main__":
    run_pairs.LOCAL.open = open_local
    run_pairs.check_program = grade_with_retry
    run_pairs.main()
    report = audit()
    (run_pairs.OUT / "audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
