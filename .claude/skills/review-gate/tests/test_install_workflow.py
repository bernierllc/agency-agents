"""install-workflow.py must not downgrade a repo's vendored aec detector.

Row: https://app.notion.com/p/41a4efecc95a81388f71da096a699f71 (origin: nevar-integrations PR #11).
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
# Only the claude-skills repo has its mirrors (scripts/, .github/) and this manifest beside the skill; an
# installed skill directory (e.g. nevar-fund's) has neither, so tests that need that layout skip there.
IN_CLAUDE_SKILLS = (SKILL.parent / "skills-manifest.json").is_file()
NOT_CLAUDE_SKILLS = "needs the claude-skills repo layout (skills-manifest.json beside the skill)"
INSTALLER = SKILL / "scripts" / "install-workflow.py"


def install(repo, *args):
    return subprocess.run([sys.executable, str(INSTALLER), *args], cwd=repo, capture_output=True, text=True)


DETECTOR = (SKILL / "scripts" / "check-forged-gate-names.py").read_bytes()
SIGNATURE = b"def forged(check_runs, run_lookup, protected=None):"
assert SIGNATURE in DETECTOR
# a newer/custom detector the bundled wrapper runs against
COMPATIBLE = b"# newer aec copy\n" + DETECTOR
# #105 Codex P2: these define every name the wrapper uses, yet the wrapper cannot run against them
INCOMPATIBLE = DETECTOR.replace(SIGNATURE, b"def forged(check_runs, run_lookup):")  # old 2-arg forged
INCOMPATIBLE_VARIANTS = (
    INCOMPATIBLE,
    b"# custom\nPROTECTED = {}\ndef forged(c, l, protected=None): return []\n"
    b"def _gh_run_lookup(repo): return None\ndef _load_check_runs(text): return []\n",  # no Review Gate entry
    b"# old custom detector\nPROTECTED = {}\ndef forged(c, l): return []\n",
    b"def broken(:\n",
    DETECTOR.replace(SIGNATURE, b"def forged(check_runs, run_lookup, protected=None, *, audit):"),  # required kw-only
)


class VendoredDetector(unittest.TestCase):
    def test_incompatible_custom_detector_refuses_without_force(self):
        # 3.2.8 P2: a KEPT detector the upgraded wrapper cannot use would fail every gate run
        with tempfile.TemporaryDirectory() as repo:
            dest = Path(repo) / "scripts" / "check-forged-gate-names.py"
            dest.parent.mkdir()
            for variant in INCOMPATIBLE_VARIANTS:
                with self.subTest(variant=variant[:40]):
                    dest.write_bytes(variant)
                    proc = install(repo)
                    self.assertEqual(proc.returncode, 1, proc.stderr)
                    self.assertIn("cannot run against", proc.stderr)
                    self.assertEqual(dest.read_bytes(), variant)
                    self.assertFalse((Path(repo) / "scripts" / "check-forged-review-gate.py").exists())
                    self.assertFalse((Path(repo) / ".github").exists())

    def test_the_installer_never_executes_the_repo_detector(self):
        # #105 Codex P1: compatibility is decided by parsing; repo code never runs on install
        with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as side:
            marker = Path(side) / "ran"
            dest = Path(repo) / "scripts" / "check-forged-gate-names.py"
            dest.parent.mkdir()
            for body in (b"open(%r, 'w').close()\nraise SystemExit(0)\n" % str(marker).encode(),
                         COMPATIBLE + b"\nopen(%r, 'w').close()\n" % str(marker).encode()):
                with self.subTest(body=body[:30]):
                    dest.write_bytes(body)
                    install(repo)
                    install(repo, "--force")
                    self.assertFalse(marker.exists())

    def test_incompatible_custom_detector_is_backed_up_and_replaced_with_force(self):
        with tempfile.TemporaryDirectory() as repo:
            dest = Path(repo) / "scripts" / "check-forged-gate-names.py"
            dest.parent.mkdir()
            dest.write_bytes(INCOMPATIBLE)
            proc = install(repo, "--force")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(dest.read_bytes(), (SKILL / "scripts" / dest.name).read_bytes())
            self.assertEqual(dest.with_name(dest.name + ".custom.bak").read_bytes(), INCOMPATIBLE)
            self.assertIn("REPLACED", proc.stderr)

    def test_a_second_forced_replacement_keeps_the_first_backup(self):
        # #105 Codex P2: the first custom copy must survive a later forced upgrade of a second one
        with tempfile.TemporaryDirectory() as repo:
            dest = Path(repo) / "scripts" / "check-forged-gate-names.py"
            dest.parent.mkdir()
            first, second = INCOMPATIBLE_VARIANTS[1], INCOMPATIBLE_VARIANTS[2]
            dest.write_bytes(first)
            self.assertEqual(install(repo, "--force").returncode, 0)
            dest.write_bytes(second)
            proc = install(repo, "--force")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(dest.with_name(dest.name + ".custom.bak").read_bytes(), first)
            self.assertEqual(dest.with_name(dest.name + ".custom.1.bak").read_bytes(), second)

    def test_differing_repo_detector_is_left_untouched_even_with_force(self):
        with tempfile.TemporaryDirectory() as repo:
            dest = Path(repo) / "scripts" / "check-forged-gate-names.py"
            dest.parent.mkdir()
            dest.write_bytes(COMPATIBLE)
            proc = install(repo, "--force")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(dest.read_bytes(), COMPATIBLE)
            self.assertIn("KEPT", proc.stderr)
            # everything else is still (re)installed
            self.assertEqual((Path(repo) / "scripts" / "check-forged-review-gate.py").read_bytes(),
                             (SKILL / "scripts" / "check-forged-review-gate.py").read_bytes())

    def test_known_older_vendored_detector_is_replaced_with_force(self):
        # #87 Codex P1: the 3.2.1-bundled detector (aec 46580fa) must be upgraded, not KEPT.
        import importlib.util
        spec = importlib.util.spec_from_file_location("iw", INSTALLER)
        iw = importlib.util.module_from_spec(spec); spec.loader.exec_module(iw)
        old = subprocess.run(["git", "show", "f599564b:review-gate/scripts/check-forged-gate-names.py"],
                             cwd=SKILL, capture_output=True)
        if old.returncode:
            self.skipTest("no git history (vendored layout)")
        import hashlib
        self.assertIn(hashlib.sha256(old.stdout).hexdigest(), iw.KNOWN_OLD)
        with tempfile.TemporaryDirectory() as repo:
            dest = Path(repo) / "scripts" / "check-forged-gate-names.py"
            dest.parent.mkdir()
            dest.write_bytes(old.stdout)
            proc = install(repo, "--force")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(dest.read_bytes(), (SKILL / "scripts" / "check-forged-gate-names.py").read_bytes())
            self.assertNotIn("KEPT", proc.stderr)

    def test_byte_identical_detector_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as repo:
            install(repo)
            dest = Path(repo) / "scripts" / "check-forged-gate-names.py"
            before = dest.stat().st_mtime_ns
            proc = install(repo, "--force")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("unchanged: " + str(dest.resolve()), proc.stdout)
            self.assertEqual(dest.stat().st_mtime_ns, before)

    def test_fresh_repo_gets_the_skill_copy(self):
        with tempfile.TemporaryDirectory() as repo:
            proc = install(repo)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual((Path(repo) / "scripts" / "check-forged-gate-names.py").read_bytes(),
                             (SKILL / "scripts" / "check-forged-gate-names.py").read_bytes())
            self.assertNotIn("KEPT", proc.stderr)

    def test_linter_is_vendored_and_runs_beside_the_checker(self):
        with tempfile.TemporaryDirectory() as repo:
            proc = install(repo)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            linter = Path(repo) / "scripts" / "lint-review-body.py"
            self.assertEqual(linter.read_bytes(), (SKILL / "scripts" / "lint-review-body.py").read_bytes())
            bad = subprocess.run([sys.executable, str(linter)], input="## Review\n\n- x\n", capture_output=True, text=True)
            self.assertEqual(bad.returncode, 1, bad.stderr)
            self.assertIn("PR body line 3:", bad.stderr)

    @unittest.skipUnless(IN_CLAUDE_SKILLS, NOT_CLAUDE_SKILLS)
    def test_this_repo_mirrors_are_byte_identical(self):
        # claude-skills runs its own gate from scripts/ and .github/workflows/; they must equal the skill's copies.
        root = SKILL.parent
        for name in ("check-review-gate.py", "check-forged-gate-names.py", "check-forged-review-gate.py",
                     "lint-review-body.py"):
            self.assertEqual((root / "scripts" / name).read_bytes(), (SKILL / "scripts" / name).read_bytes(), name)
        for linter in (root / "scripts" / "lint-review-body.py", SKILL / "scripts" / "lint-review-body.py"):
            self.assertTrue(os.access(linter, os.X_OK), linter)
        self.assertEqual((root / ".github" / "workflows" / "review-gate.yml").read_bytes(),
                         (SKILL / "templates" / "review-gate.yml").read_bytes())


DOCTOR = SKILL / "scripts" / "doctor-review-gate.py"


def doctor_script_lines(repo, env=None, *args):
    proc = subprocess.run([sys.executable, str(DOCTOR), *args], cwd=repo, capture_output=True, text=True, env=env)
    return proc, [line for line in proc.stdout.splitlines() if " scripts/" in line and "workflows" not in line]


class DoctorVendoredDrift(unittest.TestCase):
    """doctor-review-gate.py compares every vendored script with the skill's copy (3.2.12)."""

    def test_fresh_install_reports_every_vendored_script_ok(self):
        with tempfile.TemporaryDirectory() as repo:
            install(repo)
            proc, lines = doctor_script_lines(repo)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(lines, [f"OK vendored script scripts/{n}" for n in installer().VENDORED_SCRIPTS])

    def test_without_gh_the_local_checks_run_and_doctor_warns(self):
        # 3.2.13: a machine without the GitHub CLI used to crash with FileNotFoundError after the local checks
        with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as empty_path:
            install(repo)
            proc, lines = doctor_script_lines(repo, env={**os.environ, "PATH": empty_path})
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)
            self.assertIn("WARN gh (GitHub CLI) not found; skip label and ruleset checks", proc.stdout)
            self.assertEqual(lines, [f"OK vendored script scripts/{n}" for n in installer().VENDORED_SCRIPTS])

    @unittest.skipUnless(IN_CLAUDE_SKILLS, NOT_CLAUDE_SKILLS + " and its git history")
    def test_an_old_checker_and_a_missing_linter_warn(self):
        old = subprocess.run(["git", "show", "bce2e9c0:review-gate/scripts/check-review-gate.py"],
                             cwd=SKILL, capture_output=True, check=True).stdout  # review-gate 3.2.10
        with tempfile.TemporaryDirectory() as repo:
            install(repo)
            (Path(repo) / "scripts" / "check-review-gate.py").write_bytes(old)
            (Path(repo) / "scripts" / "lint-review-body.py").unlink()
            proc, lines = doctor_script_lines(repo)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("WARN scripts/check-review-gate.py differs from the skill; re-run "
                          "install-workflow.py --force and merge it to the default branch", lines)
            self.assertIn("WARN missing scripts/lint-review-body.py; re-run install-workflow.py and merge it "
                          "to the default branch", lines)
            self.assertIn("OK vendored script scripts/check-forged-review-gate.py", lines)
            # one line per vendored script, taken from the installer's own list
            self.assertEqual(len(lines), len(installer().VENDORED_SCRIPTS), lines)


class InstalledSkillLayout(unittest.TestCase):
    """The skill's tests also run from an installed skill directory, without the claude-skills tree."""

    @unittest.skipUnless(IN_CLAUDE_SKILLS, "already running from an installed skill directory")
    def test_module_skips_repo_layout_tests_outside_claude_skills(self):
        with tempfile.TemporaryDirectory() as d:
            skill = Path(d) / "skills" / "review-gate"
            shutil.copytree(SKILL, skill, ignore=shutil.ignore_patterns("__pycache__"))
            proc = subprocess.run([sys.executable, "-m", "unittest", "-v", "test_install_workflow"],
                                  cwd=skill / "tests", capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertRegex(proc.stderr, r"test_this_repo_mirrors_are_byte_identical .*skipped 'needs the claude-skills")
            self.assertNotIn("FileNotFoundError", proc.stderr)


def installer():
    spec = importlib.util.spec_from_file_location("install_workflow", INSTALLER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod



class DoctorStrict(unittest.TestCase):
    """3.2.14: --strict exits 1 on workflow or vendored-script drift; the default run still exits 0."""

    def no_gh(self):
        self._path = tempfile.TemporaryDirectory()
        self.addCleanup(self._path.cleanup)
        return {**os.environ, "PATH": self._path.name}  # local checks only, as in CI without a token

    def test_checker_vendored_without_closer_permissions_fails_strict(self):
        src = (SKILL / "scripts" / "check-review-gate.py").read_text()
        start = src.index("def closer_permissions(")
        stale = src[:start] + src[src.index("\ndef ", start + 1) + 1:]  # an old copy without the function
        self.assertNotIn("def closer_permissions(", stale)
        with tempfile.TemporaryDirectory() as repo:
            install(repo)
            (Path(repo) / "scripts" / "check-review-gate.py").write_text(stale)
            default, _ = doctor_script_lines(repo, self.no_gh())
            strict, lines = doctor_script_lines(repo, self.no_gh(), "--strict")
            self.assertEqual(default.returncode, 0, default.stdout)
            self.assertEqual(strict.returncode, 1, strict.stdout)
            self.assertIn("WARN scripts/check-review-gate.py differs from the skill; re-run "
                          "install-workflow.py --force and merge it to the default branch", lines)
            self.assertIn("FAIL --strict: 1 workflow/vendored-script problem(s) above", strict.stdout)

    def test_fresh_install_passes_strict(self):
        with tempfile.TemporaryDirectory() as repo:
            install(repo)
            proc, _ = doctor_script_lines(repo, self.no_gh(), "--strict")
            self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_missing_workflow_and_script_fail_strict(self):
        with tempfile.TemporaryDirectory() as repo:
            install(repo)
            (Path(repo) / ".github" / "workflows" / "review-gate.yml").unlink()
            (Path(repo) / "scripts" / "lint-review-body.py").unlink()
            proc, _ = doctor_script_lines(repo, self.no_gh(), "--strict")
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("FAIL --strict: 2 ", proc.stdout)

    def test_a_kept_newer_aec_detector_passes_strict(self):
        # the installer keeps it, so --strict must not fail a repo for what --force would not change
        with tempfile.TemporaryDirectory() as repo:
            install(repo)
            (Path(repo) / "scripts" / "check-forged-gate-names.py").write_bytes(COMPATIBLE)
            proc, lines = doctor_script_lines(repo, self.no_gh(), "--strict")
            self.assertEqual(proc.returncode, 0, proc.stdout)
            self.assertTrue(any(line.startswith("WARN scripts/check-forged-gate-names.py differs") for line in lines))


class DoctorJob(unittest.TestCase):
    """3.2.14: install-workflow.py --doctor-job writes an optional CI job running doctor --strict."""

    def test_written_only_on_request(self):
        with tempfile.TemporaryDirectory() as repo:
            install(repo)
            self.assertFalse((Path(repo) / ".github" / "workflows" / "review-gate-doctor.yml").exists())
            install(repo, "--doctor-job")
            written = (Path(repo) / ".github" / "workflows" / "review-gate-doctor.yml").read_bytes()
            self.assertEqual(written, (SKILL / "templates" / "review-gate-doctor.yml").read_bytes())

    def test_job_runs_strict_from_claude_skills_main_with_no_paths_filter(self):
        import yaml
        wf = yaml.safe_load((SKILL / "templates" / "review-gate-doctor.yml").read_text())
        on = wf[True]  # YAML 1.1 reads the `on` key as True
        self.assertEqual(on, "pull_request")  # no paths filter, no branch filter
        self.assertEqual(wf["permissions"], {"contents": "read"})
        steps = wf["jobs"]["doctor"]["steps"]
        self.assertEqual(len(steps), 2)
        run = steps[1]["run"]
        self.assertIn("https://github.com/bernierllc/claude-skills", run)
        self.assertTrue(run.endswith("/review-gate/scripts/doctor-review-gate.py\" --strict"), run)
        self.assertNotIn("${{", run)  # nothing from the event is interpolated into the shell


if __name__ == "__main__":
    unittest.main()
