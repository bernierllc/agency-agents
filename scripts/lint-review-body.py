#!/usr/bin/env python3
"""Lint a PR body against the Review Gate body rules before you push or edit it.

usage: python3 scripts/lint-review-body.py [BODY_FILE]   (reads stdin when no file or "-")

Runs the gate's own `review_region` from check-review-gate.py beside this file, so the two cannot
drift. Exit 0 when the body passes, 1 with one line per problem (line number and offending construct)
when it does not. It checks the body rules and the shape of every `Fallback review:` line (the checker's
own FALLBACK_ATTESTATION, so a short SHA fails here as it does in the gate); whether that SHA is the
current head is the gate's job.
"""
from __future__ import annotations

import functools
import importlib.util
import sys
from pathlib import Path

# A module constant, not __doc__: `python -O` drops docstrings.
USAGE = 'usage: python3 scripts/lint-review-body.py [BODY_FILE]   (reads stdin when no file or "-")'


@functools.lru_cache(maxsize=None)
def _load_gate():
    """Load check-review-gate.py beside the real file (resolve() follows a symlinked linter)."""
    path = Path(__file__).resolve().with_name("check-review-gate.py")
    try:
        spec = importlib.util.spec_from_file_location("check_review_gate", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except OSError as e:
        print(f"review-gate body: cannot load {path}: {e}; re-run install-workflow.py --force", file=sys.stderr)
        raise SystemExit(2)
    if not hasattr(mod, "review_region"):  # a checker older than 3.2.8, vendored before this linter
        print(f"review-gate body: {path} is too old for this linter (no review_region); "
              "re-run install-workflow.py --force", file=sys.stderr)
        raise SystemExit(2)
    return mod


def lint(body: str) -> list[str]:
    gate = _load_gate()  # loaded on first use, so --help works without a checker
    region, problems = gate.review_region(body)
    for line in region:
        if line.lower().startswith("fallback review:") and not gate.FALLBACK_ATTESTATION.fullmatch(line):
            problems.append(f"## Review line {line!r} is not an exact attestation: Fallback review: "
                            "<codex|agy|antigravity|superpowers|claude-sonnet> on <full 40-hex head SHA> "
                            "— verdict: <clean|findings fixed>")
    return problems


def main(argv: list[str]) -> int:
    if argv and argv[0] in ("-h", "--help"):
        print(USAGE)
        return 0
    if len(argv) > 1:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        body = sys.stdin.read() if not argv or argv[0] == "-" else Path(argv[0]).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:  # a bad path is a usage error (2), never a lint verdict (1)
        print(f"review-gate body: cannot read {argv[0] if argv else 'stdin'}: {e}", file=sys.stderr)
        return 2
    problems = lint(body)
    for p in problems:
        print(f"review-gate body: {p}", file=sys.stderr)
    if not problems:
        print("review-gate body: OK")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
