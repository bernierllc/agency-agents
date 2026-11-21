"""Run: python3 review-gate/tests/test_lint_review_body.py"""
import importlib.util
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
LINTER = SCRIPTS / "lint-review-body.py"


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


g = _load("check_review_gate", "check-review-gate.py")
HEAD = "0123456789abcdef0123456789abcdef01234567"
ATT = f"Fallback review: claude-sonnet on {HEAD} — verdict: clean"
OK = f"## Summary\n\n- a list, `code` and [a link](https://x.y) are fine here\n\n## Review\n\n{ATT}\nTwo P2s were fixed.\n\n## Notes\n\n- footer\n"


def body(review_line=None, top=None):
    """Body with one extra line in ## Review (line 6) or above it (line 3)."""
    return (f"Summary\n\n{top}\n\n" if top is not None else "Summary\n\n") + "## Review\n\n" + ATT + "\n" + \
        (f"{review_line}\n" if review_line is not None else "")


def lint_cli(text):
    r = subprocess.run([sys.executable, str(LINTER)], input=text, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def gate_body_reasons(text):
    """What the gate itself says about this body, with the attestation and label satisfied."""
    reasons = g.evaluate({"body": text, "headRefOid": HEAD, "baseRefName": "main", "reviews": {"nodes": []},
                          "labels": {"nodes": [{"name": "review:high"}]}, "reviewThreads": {"nodes": []}})
    return reasons


# a valid body passes, by file, by stdin and by "-"
rc, out = lint_cli(OK)
assert rc == 0 and "OK" in out, out
assert gate_body_reasons(OK) == []
with __import__("tempfile").NamedTemporaryFile("w", suffix=".md", delete=False) as f:
    f.write(OK)
try:
    assert subprocess.run([sys.executable, str(LINTER), f.name], capture_output=True).returncode == 0
finally:
    Path(f.name).unlink()
assert subprocess.run([sys.executable, str(LINTER), "-"], input=OK, capture_output=True, text=True).returncode == 0
assert subprocess.run([sys.executable, str(LINTER), "a", "b"], capture_output=True).returncode == 2
# an unreadable or non-UTF-8 file is a usage error (2) naming the path, not a traceback or a lint failure (1)
with __import__("tempfile").TemporaryDirectory() as d:
    (Path(d) / "latin1.md").write_bytes(b"## Review\n\ncaf\xe9\n")
    for path in (Path(d) / "missing.md", Path(d), Path(d) / "latin1.md"):
        r = subprocess.run([sys.executable, str(LINTER), str(path)], capture_output=True, text=True)
        assert r.returncode == 2 and "cannot read" in r.stderr and "Traceback" not in r.stderr, (path, r.stderr)

# --help is not a path; usage survives `python -O` (which drops docstrings)
r = subprocess.run([sys.executable, str(LINTER), "--help"], capture_output=True, text=True)
assert r.returncode == 0 and r.stdout.startswith("usage:"), r
r = subprocess.run([sys.executable, "-O", str(LINTER), "a", "b"], capture_output=True, text=True)
assert r.returncode == 2 and r.stderr.startswith("usage:"), r
# a symlinked linter finds the checker beside the real file; a missing or pre-review_region checker is exit 2
with __import__("tempfile").TemporaryDirectory() as d:
    d = Path(d)
    (d / "link.py").symlink_to(LINTER)
    r = subprocess.run([sys.executable, str(d / "link.py")], input=OK, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    (d / "lint-review-body.py").write_bytes(LINTER.read_bytes())
    r = subprocess.run([sys.executable, str(d / "lint-review-body.py"), "--help"], capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.startswith("usage:"), r  # help needs no checker (Codex P2 on #119)
    r = subprocess.run([sys.executable, str(d / "lint-review-body.py")], input=OK, capture_output=True, text=True)
    assert r.returncode == 2 and "cannot load" in r.stderr and "install-workflow.py --force" in r.stderr, r.stderr
    (d / "check-review-gate.py").write_text("def evaluate(pr):\n    return []\n")  # a pre-3.2.8 checker
    r = subprocess.run([sys.executable, str(d / "lint-review-body.py")], input=OK, capture_output=True, text=True)
    assert r.returncode == 2 and "too old" in r.stderr and "Traceback" not in r.stderr, r.stderr

# every banned construct in ## Review fails on its own line (line 5 + 1 = 6 here), naming it
REVIEW_BAD = {
    "- a bullet": "starts with '-'",
    "* a bullet": "starts with '*'",
    "+ a bullet": "starts with '+'",
    "1. ordered": "ordered-list marker",
    "2) ordered": "ordered-list marker",
    "> a quote": "starts with '>'",
    " leading space": "starts with ' '",
    "## Reviews heading": None,  # a later `## ` line ends the region: not a failure
}
for ch in "`<>|[]()*_~$":
    REVIEW_BAD[f"Fixed the{ch}thing"] = f"character {ch!r} at column 10"
for line, want in REVIEW_BAD.items():
    text = body(line)
    rc, out = lint_cli(text)
    if want is None:
        assert rc == 0, (line, out)
        continue
    assert rc == 1 and "PR body line 6:" in out and want in out, (line, out)

# whole-body bans fail anywhere, above ## Review too (line 3)
TOP_BAD = {
    "```": "code fences",
    "  ~~~python": "code fences",
    "see <!-- hidden": "HTML comments",
    "<div>": "raw HTML",
    "- <b>x</b>": "raw HTML",
    "> <pre>": "raw HTML",
    "text <details> x": "<details>",
    "<DETAILS open>": "<details>",
}
for line, want in TOP_BAD.items():
    rc, out = lint_cli(body(top=line))
    assert rc == 1 and "PR body line 3:" in out and want in out, (line, out)

# structure: no heading, two headings, heading not after a blank line
for text, want in (("Summary\n", "found 0"), ("## Review\n\nx\n\n## Review\n", "found 2"),
                   ("Summary\n## Review\n", "line 2: '## Review' must follow a blank line")):
    rc, out = lint_cli(text)
    assert rc == 1 and want in out, (text, out)

# parity: on every fixture the linter's problems are exactly the gate's body reasons, and the linter passes
# a body exactly when the gate passes it (attestation and label satisfied), so drift fails CI
lint = _load("lint_review_body", "lint-review-body.py")
fixtures = [OK, body(), *(body(l) for l in REVIEW_BAD), *(body(top=l) for l in TOP_BAD),
            "Summary\n", "## Review\n\nx\n\n## Review\n", "Summary\n## Review\n", "Summary\r\n\r\n## Review\r\n\r\n" + ATT]
for text in fixtures:
    problems = lint.lint(text)
    reasons = gate_body_reasons(text)
    assert set(problems) == {r for r in reasons if r.startswith("PR body")}, (text, problems, reasons)
    assert (problems == []) == (reasons == []), (text, problems, reasons)
    rc, out = lint_cli(text)
    assert rc == (1 if problems else 0) and all(p in out for p in problems), (text, out)

# golden corpus: verdicts fixed by hand from the rule-2 grammar, not derived from review_region, so a change
# to what the gate accepts fails here even though the parity check above would still hold
GOLDEN = [
    (OK, True),
    (f"## Review\n\n{ATT}\n", True),  # heading on the first line
    (f"Summary\n\n## Review\n\n{ATT}\nFixed 3 of 4 issues, all P2.\n", True),
    (f"Summary\n\n## Review\n\n{ATT}\n\n## Notes\n\n- list, `code` and <b>x</b> inline\n", True),
    (f"Summary\n## Review\n\n{ATT}\n", False),  # heading not after a blank line
    (f"Summary\n\n## Review\n\n{ATT}\n- a bullet\n", False),
    (f"Summary\n\n## Review\n\n{ATT}\n2. note\n", False),
    (f"Summary\n\n## Review\n\n{ATT}\nFixed a_b\n", False),
    (f"Summary\n\n## Review\n\n{ATT}\n\u00a0\n", False),  # NBSP-only is not blank
    (f"<div>\n\n## Review\n\n{ATT}\n", False),
    (f"- <b>x</b>\n\n## Review\n\n{ATT}\n", False),
    (f"text <details> x\n\n## Review\n\n{ATT}\n", False),
    (f"```\nx\n```\n\n## Review\n\n{ATT}\n", False),
    (f"## Reviews\n\n{ATT}\n", False),  # no ## Review section
]
for text, passes in GOLDEN:
    assert (gate_body_reasons(text) == []) == passes, (text, gate_body_reasons(text))
    assert (lint_cli(text)[0] == 0) == passes, (text, lint_cli(text))

# the linter has no grammar of its own: it reaches the checker's review_region
src = LINTER.read_text()
assert "review_region" in src and "re.compile" not in src and "import re" not in src
print("lint ok")

# 3.2.13: a Fallback review line with a short SHA fails the linter AND the gate; the full 40-hex head passes both.
# The linter uses the checker's FALLBACK_ATTESTATION, so the two shapes cannot drift.
_short = f"Summary\n\n## Review\n\nFallback review: claude-sonnet on {HEAD[:7]} — verdict: clean\n"
_full = f"Summary\n\n## Review\n\nFallback review: claude-sonnet on {HEAD} — verdict: clean\n"
rc, out = lint_cli(_short)
assert rc == 1 and "not an exact attestation" in out and "full 40-hex head SHA" in out, out
assert any("Fallback review" in r for r in gate_body_reasons(_short)), gate_body_reasons(_short)
rc, out = lint_cli(_full)
assert rc == 0, out
assert gate_body_reasons(_full) == []
# prose that only mentions a fallback review mid-line is not an attestation and is not checked
rc, out = lint_cli(_full + "Round 2 used a fallback review: same verdict.\n")
assert rc == 0, out
assert "FALLBACK_ATTESTATION" in Path(LINTER).read_text() and "re.compile" not in Path(LINTER).read_text()
print("lint attestation tests passed")
