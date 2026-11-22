"""Runs inside a disposable, offline Python container. Read one JSON request."""
import ast
import itertools
import json
import sys


BUILTINS = {f.__name__: f for f in (
    abs, all, any, bool, dict, enumerate, filter, int, len, list, map, max, min,
    next, range, reversed, set, sorted, sum, tuple, zip, itertools.groupby, itertools.pairwise)}
METHODS = {"count", "index", "get", "items", "keys", "values", "fromkeys"}


def grade(request):
    expression = request["expression"].strip()
    cases = request["cases"]
    try:
        tree = ast.parse(expression, mode="eval")
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr not in METHODS:
                raise ValueError("unsupported attribute")
            if isinstance(node, ast.Name) and node.id.startswith("_"):
                raise ValueError("unsupported name")
            if isinstance(node, (ast.Await, ast.Yield, ast.YieldFrom)):
                raise ValueError("unsupported expression")
        code = compile(tree, "<submission>", "eval")
    except (SyntaxError, ValueError) as exc:
        return {"passed": 0, "correct": 0, "total": len(cases), "example": str(exc)[:180]}
    correct = 0
    first = None
    for xs, k, expected in cases:
        try:
            value = eval(code, {"__builtins__": BUILTINS, "xs": xs.copy(), "k": k})
            ok = (type(value) is type(expected) and value == expected
                  and (type(value) is not list or all(type(x) is int for x in value)))
            detail = repr(value)[:100]
        except Exception as exc:
            ok, detail = False, type(exc).__name__ + ": " + str(exc)[:100]
        if ok:
            correct += 1
        elif first is None:
            first = {"xs": xs, "k": k, "wanted": expected, "got": detail}
    return {"passed": int(correct == len(cases)), "correct": correct,
            "total": len(cases), "example": first}


if __name__ == "__main__":
    print(json.dumps(grade(json.load(sys.stdin))))
