"""Run: python3 pr-merge-flow/tests/test_pr_guard_parity.py  (exits non-zero on a lost block or a head crash).

Differential check (plans/pr-guard-shell-parsing-design.md, step 1): every command the previous release blocked,
this guard must still block. The baseline is the newest pr-merge-flow commit on origin/main whose SKILL.md version
is lower than this tree's. Inputs: every command the head and baseline test files pass to a guard function, plus
fixtures/pr_guard_inputs.txt. Each runs under eight stubs (base staging/main x checks green/red x the dir an
unpinned fork or not).
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
REPO = SKILL.parent
TMP = os.path.realpath(tempfile.gettempdir())
M = "@" + "codex"

# (cmd, cwd) pairs whose block the head may drop, cwd "<tmp>" for a test's temp dir. Each: reason, approval.
ALLOWED_FLIPS = {
    **{(f"gh pr comment 1 --body '{M[:k]}\\\n{M[k:]} review'", "<tmp>"):
       "single quotes keep backslash-newline, so no mention is posted (plan step 3, issue #124, PR #125)"
       for k in range(1, len(M))},
    ('gh api -X GET repos/o/r/issues -F labels=@"$LABEL_FILE"', "<tmp>"):
        "read-only GET posts no comment (plan step 3, issue #124, PR #125)",
    ('gh api -X GET repos/o/r/issues --input "$B"', "<tmp>"):
        "read-only GET posts no comment (plan step 3, issue #124, PR #125)",
}

GUARD_FUNCS = ("check", "sync_calls", "merge_calls", "draft_violation", "comment_posts", "codex_mention_post",
               "body_file_block", "polls", "runs_async", "segments", "pr_create_dirs", "walk", "shell_comments",
               "has_override")
CONFIGS = [dict(base=b, green=gr, fork=f) for b in ("staging", "main") for gr in (True, False) for f in (False, True)]


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True).stdout


def version(skill_md):
    m = re.search(r"^version:\s*(\S+)", skill_md, re.M)
    return tuple(int(x) for x in m.group(1).split(".")) if m else None


def baseline():
    """(sha, version) of the newest origin/main commit touching pr-merge-flow/ with a lower SKILL.md version."""
    head = version((SKILL / "SKILL.md").read_text())
    for sha in git("log", "--format=%H", "origin/main", "--", "pr-merge-flow/").split():
        try:
            v = version(git("show", f"{sha}:pr-merge-flow/SKILL.md"))
        except subprocess.CalledProcessError:
            continue
        if v and v < head:
            return sha, v
    sys.exit(f"FAIL: no commit on origin/main has a pr-merge-flow version below {head}")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def stubbed(name, path, cfg):
    m = load(name, path)
    m.pr_state = lambda d, b=cfg["base"]: (b, "CLEAN")
    m.not_green = (lambda *a, **k: "") if cfg["green"] else (lambda *a, **k: "red")
    m.unpinned_fork = (lambda d: "o/r (fork of u/r)") if cfg["fork"] else (lambda d: None)
    m.draft_mode = lambda *a, **k: False
    m.fb_log = lambda *a, **k: None
    return m


def main():
    t0 = time.monotonic()
    sha, bver = baseline()
    print(f"baseline {sha[:12]} (pr-merge-flow {'.'.join(map(str, bver))})")
    work = Path(tempfile.mkdtemp())
    (work / "old.py").write_text(git("show", f"{sha}:pr-merge-flow/scripts/pr-guard.py"))
    (work / "old_test.py").write_text(git("show", f"{sha}:pr-merge-flow/tests/test_pr_guard.py"))
    pairs = [(stubbed(f"old{i}", work / "old.py", c), stubbed(f"new{i}", SKILL / "scripts" / "pr-guard.py", c))
             for i, c in enumerate(CONFIGS)]
    seen, lost, crashed, gained, flipped = set(), [], [], 0, set()

    def compare(cmd, cwd):
        nonlocal gained
        if not isinstance(cmd, str) or (cmd, cwd) in seen:
            return
        seen.add((cmd, cwd))
        key = (cmd, "<tmp>" if os.path.realpath(cwd).startswith(TMP) else cwd)
        for (old, new), cfg in zip(pairs, CONFIGS):
            try:
                was = old.check(cmd, cwd) is not None
            except Exception:  # a baseline crash counts as a block: the head must block it (plan step 1)
                was = True
            try:
                now = new.check(cmd, cwd) is not None
            except Exception as e:
                crashed.append((cmd, cwd, cfg, repr(e)))
                continue
            if was and not now:
                (flipped.add(key) if key in ALLOWED_FLIPS else lost.append((cmd, cwd, cfg)))
            gained += now and not was

    def replay(test_file, guard):
        """Run a test file against `guard`, recording every command it hands a guard function (not the
        guard's own nested calls, whose second argument is not the cwd)."""
        src = test_file.read_text()
        hook = ("import os as _os\nfor _n in %r:\n"
                "    _f = getattr(g, _n, None)\n"
                "    if _f is None: continue\n"
                "    def _w(*a, _f=_f, **k):\n"
                "        cmd = a[0] if a else k.get('cmd')\n"
                "        cwd = a[1] if len(a) > 1 and isinstance(a[1], str) else _os.getcwd()\n"
                "        __depth[0] += 1\n"
                "        try:\n"
                "            if __depth[0] == 1: __compare(cmd, cwd)\n"
                "            return _f(*a, **k)\n"
                "        finally: __depth[0] -= 1\n"
                "    setattr(g, _n, _w)\n") % (GUARD_FUNCS,)
        anchor = "spec.loader.exec_module(g)\n"
        assert anchor in src, f"{test_file}: can't find where the guard is loaded"
        src = src.replace(anchor, anchor + hook, 1)
        src = src.replace('Path(__file__).parent.parent / "scripts" / "pr-guard.py"', repr(str(guard)))
        exec(compile(src, str(test_file), "exec"), {"__compare": compare, "__depth": [0], "__name__": "__main__", "__file__": str(test_file)})

    replay(HERE / "test_pr_guard.py", SKILL / "scripts" / "pr-guard.py")
    replay(work / "old_test.py", work / "old.py")  # a deleted test case still contributes its input
    for line in (HERE / "fixtures" / "pr_guard_inputs.txt").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            cwd, cmd = json.loads(line)
            compare(cmd, cwd)

    for cmd, cwd, cfg, err in crashed:
        print(f"CRASH head {cfg} cwd={cwd}: {cmd!r}: {err}")
    for cmd, cwd, cfg in lost:
        print(f"LOST block {cfg} cwd={cwd}: {cmd!r}")
    for key in ALLOWED_FLIPS.keys() - flipped:  # the list stays exact: an entry that no longer flips is removed
        print(f"STALE allowed flip (no input flips it): {key!r}")
    print(f"inputs={len(seen)} comparisons={len(seen) * len(CONFIGS)} lost={len(lost)} crashed={len(crashed)} "
          f"new_blocks={gained} allowed_flips={len(ALLOWED_FLIPS)} wall={time.monotonic() - t0:.1f}s")
    if lost or crashed or ALLOWED_FLIPS.keys() - flipped:
        sys.exit(1)


def test_pr_guard_parity():
    """pytest entry point."""
    main()


if __name__ == "__main__":
    main()
