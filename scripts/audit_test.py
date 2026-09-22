# Copyright (c) 2026 A.I. Hero, Inc.
# All Rights Reserved.

"""Tables for audit.py's parsers. Run: python3 -m unittest scripts/audit_test.py

Each parser here has the failure mode the Justfile names for the hook tests:
matching nothing is indistinguishable from a clean input, so a regression
reads as a fleet that got better."""

import contextlib
import importlib.util
import io
import os
import pathlib
import json
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("audit", HERE / "audit.py")
audit = importlib.util.module_from_spec(spec)
sys.modules["audit"] = audit  # the fleet's checkers.py does `import audit`
CLEAN_ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
spec.loader.exec_module(audit)


def write(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def git(cwd, *args):
    # Strip GIT_* from the environment: under a pre-commit hook (and in a
    # linked worktree) GIT_DIR/GIT_INDEX_FILE point at the repo being
    # committed, and every fixture `git init`/`commit` would hit it instead.
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, env=CLEAN_ENV)


def git_repo(root, name):
    """A committed repo with one file, so ls-files / worktree add work."""
    r = root / name
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    git(r, "config", "user.email", "t@example.com")
    git(r, "config", "user.name", "t")
    write(r, "README.md", "x\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "init")
    return r


class WorkflowOn(unittest.TestCase):
    def test_forms(self):
        cases = {
            "on:\n  push:\n": {"push": None},
            "on: [push, pull_request]\n": {"push": None, "pull_request": None},
            "on: push\n": {"push": None},
            '"on":\n  push:\n': {"push": None},
        }
        for text, want in cases.items():
            with tempfile.TemporaryDirectory() as d:
                w = write(pathlib.Path(d), "ci.yaml", text)
                self.assertEqual(audit._wf_on(audit._wf_doc(w)), want, text)

    def test_unreadable_is_manual_not_pass(self):
        with tempfile.TemporaryDirectory() as d:
            r = pathlib.Path(d)
            write(r, ".github/workflows/ci.yaml", "on:\n  pull_request:\n    paths: [x]\n\tbad\n")
            st, detail = audit.CHECKS["CI-21"](r)
            self.assertEqual(st, audit.MANUAL)
            self.assertIn("ci.yaml", detail)

    def test_list_form_passes_ci21(self):
        with tempfile.TemporaryDirectory() as d:
            r = pathlib.Path(d)
            write(r, ".github/workflows/ci.yaml", "on: [push, pull_request]\njobs: {}\n")
            self.assertEqual(audit.CHECKS["CI-21"](r), (audit.PASS, ""))


class ImageRefs(unittest.TestCase):
    def test_dockerfile(self):
        text = (
            "FROM --platform=$BUILDPLATFORM golang:1.22 AS build\n"
            "FROM node:20-alpine as ui\nFROM ui\nFROM scratch\nFROM ${BASE}\n"
            "FROM alpine@sha256:abc\nFROM redis:latest\nFROM mongo\n"
            "FROM myreg:5000/mongo:8.0\n"
        )
        with tempfile.TemporaryDirectory() as d:
            f = write(pathlib.Path(d), "Dockerfile.dev", text)
            self.assertEqual(audit._image_refs(f), [
                ("golang", "1.22"), ("node", "20-alpine"), ("redis", "latest"),
                ("mongo", ""), ("mongo", "8.0"),
            ])

    def test_compose_ignores_comments(self):
        text = "services:\n  a:\n    image: 'minio/minio:latest'\n  b:\n    image: mongo:8\n  # image: bad:latest\n  c:\n    image: ${IMG}\n"
        with tempfile.TemporaryDirectory() as d:
            f = write(pathlib.Path(d), "docker-compose.dev.yaml", text)
            self.assertEqual(audit._image_refs(f), [("minio", "latest"), ("mongo", "8")])

    def test_ctr09_and_ctr11(self):
        with tempfile.TemporaryDirectory() as d:
            r = pathlib.Path(d)
            write(r, "Dockerfile.dev", "FROM mongo:8\nFROM redis:latest\nFROM golang:1.22 AS build\nFROM build\n")
            write(r, "docker-compose.prod.yaml", "services:\n  mongo:\n    image: mongo:8.0\n    command: [--replSet, rs0]\n")
            write(r, "dev.sh", "mongod --replSet rs0\n")
            st, detail = audit.CHECKS["CTR-09"](r)
            self.assertEqual(st, audit.FAIL)
            self.assertIn("redis:latest", detail)
            self.assertNotIn("golang", detail)
            self.assertEqual(audit.CHECKS["CTR-11"](r)[0], audit.PASS, "8 and 8.0 are one major")


class HookSegments(unittest.TestCase):
    PC = "repos:\n- repo: a\n  hooks:\n  - id: markdownlint\n    args: [--fix]\n  - id: codespell\n    args: [--disable=x]\n- repo: b\n  hooks:\n  - id: semgrep\n    # a comment\n    args:\n    - --config=auto\n    - --error\n"

    def test_segment_scopes_args(self):
        seg = audit._hook_segment(self.PC, "markdownlint")
        self.assertIn("--fix", seg)
        self.assertNotIn("--disable", seg)
        self.assertIn("--config=auto", audit._hook_segment(self.PC, "semgrep"))
        self.assertEqual(audit._hook_segment(self.PC, "ruff"), "")


class References(unittest.TestCase):
    def test_three_outcomes(self):
        with tempfile.TemporaryDirectory() as d:
            r = pathlib.Path(d)
            ref = write(r, "ref.md", "## Fleet\nbody\n")
            self.assertEqual(audit._matches_reference(r / "x", r / "absent")[0], audit.MANUAL)
            self.assertEqual(audit._matches_reference(r / "absent", ref)[0], audit.FAIL)
            same = write(r, "same.md", "## Fleet\nbody\n")
            self.assertEqual(audit._matches_reference(same, ref)[0], audit.PASS)
            doc = write(r, "AGENTS.md", "# A\n\n## Fleet\nbody\n\n## Next\nz\n")
            self.assertEqual(audit._matches_reference(doc, ref, audit._fleet_section)[0], audit.PASS)
            nodoc = write(r, "B.md", "# A\n")
            self.assertEqual(audit._matches_reference(nodoc, ref, audit._fleet_section), (audit.FAIL, "section absent"))

    def test_fleet_section_slices(self):
        self.assertIsNone(audit._fleet_section("# A\n"))
        self.assertEqual(audit._fleet_section("x\n## Fleet\nb\n"), "## Fleet\nb\n")
        self.assertEqual(audit._fleet_section("x\n## Fleet\nb\n## C\nd\n"), "## Fleet\nb")


class HookRevs(unittest.TestCase):
    def tearDown(self):
        audit._FLEET.clear()

    def run_pre07(self, mine, by_repo):
        with tempfile.TemporaryDirectory() as d:
            r = pathlib.Path(d) / "fx"
            write(r, ".pre-commit-config.yaml", "repos: []\n")
            audit._FLEET["revs"] = {"https://h/hooks": {**by_repo, "fx": mine}}
            audit._FLEET["revs-broken"] = {}
            return audit.CHECKS["PRE-07"](r)

    def test_majority(self):
        self.assertEqual(self.run_pre07("v0.9.0", {"a": "v1.0.0", "b": "v1.0.0"})[0], audit.FAIL)
        self.assertEqual(self.run_pre07("v1.5.0", {"a": "v1.0.0", "b": "v2.0.0"})[0], audit.FAIL, "tie goes to newest")
        self.assertEqual(self.run_pre07("v0.9.0", {"a": "v1.0.0"})[0], audit.PASS, "under three voters")


class Snapshot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        # FAMILY is bound by configure() from FLEET.md (or the lone repo), so
        # the fixture binds its own: the snapshot walks family_repos().
        self.saved = audit.ROOT, audit.FAMILY, dict(audit.REPO_DIR)
        audit.ROOT, audit.FAMILY = self.root, ("hero-template",)
        audit.REPO_DIR.clear()
        # Mapped under a subdirectory, so cleanup must go through REPO_DIR: a
        # regression to `ROOT / rn` would leave the worktree behind and the
        # count below would still read 1 only by accident of the fallback.
        audit.REPO_DIR["hero-template"] = self.root / "sub" / "hero-template"
        (self.root / "sub").mkdir()
        git_repo(self.root / "sub", "hero-template")

    def tearDown(self):
        audit.ROOT, audit.FAMILY, saved_dirs = self.saved
        audit.REPO_DIR.clear()
        audit.REPO_DIR.update(saved_dirs)
        self.tmp.cleanup()

    def worktrees(self):
        out = subprocess.run(["git", "worktree", "list"], cwd=self.root / "sub" / "hero-template",
                             capture_output=True, text=True, env=CLEAN_ENV).stdout
        return out.strip().splitlines()

    def test_cleanup_on_exception(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(RuntimeError):
                with audit.snapshot_family("HEAD"):
                    self.assertNotEqual(audit.repo_path("hero-template"), self.root / "sub" / "hero-template")
                    self.assertEqual(audit.repo_path("hero-template").name, "hero-template")
                    raise RuntimeError("boom")
        self.assertEqual(audit.REPO_PATH, {})
        self.assertEqual(audit._FLEET, {})
        self.assertEqual(len(self.worktrees()), 1)

    def test_unknown_ref_audits_checkout(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with audit.snapshot_family("no-such-ref"):
                self.assertEqual(audit.repo_path("hero-template"), self.root / "sub" / "hero-template")
        self.assertEqual(len(self.worktrees()), 1)


class AppliesTo(unittest.TestCase):
    """applies_to resolves FLEET.md groups and leaves every other name to
    the checkers. A capability name must never exempt a repo on its own:
    the explicit lists it used to resolve to went stale and hid three
    template clones from every Go and Node check."""
    def setUp(self):
        self.saved = dict(audit.GROUP_REPOS)
        audit.GROUP_REPOS.clear()
        audit.GROUP_REPOS.update({"apps": {"a", "b"}, "infra": {"tf"}})

    def tearDown(self):
        audit.GROUP_REPOS.clear(); audit.GROUP_REPOS.update(self.saved)

    def test_groups(self):
        self.assertTrue(audit.applies({"applies_to": "all"}, "tf"))
        self.assertTrue(audit.applies({}, "tf"))
        self.assertTrue(audit.applies({"applies_to": ["template", "apps"]}, "a"))
        self.assertFalse(audit.applies({"applies_to": ["template", "apps"]}, "tf"))
        self.assertTrue(audit.applies({"applies_to": "go"}, "tf"), "a capability is the checker's call")
        self.assertTrue(audit.applies({"applies_to": ["go", "apps"]}, "a"))
        self.assertFalse(audit.applies({"applies_to": ["go", "apps"]}, "tf"), "the group half still decides")

    def test_no_fleet_reaches_everyone(self):
        audit.GROUP_REPOS.clear()
        self.assertTrue(audit.applies({"applies_to": ["apps"]}, "anything"))


def fleet_fixture(root, fleet_md, overlay=None, checkers=None):
    """A fleet folder: FLEET.md, a `.fleet/` register with the given overlay
    text (or an empty one), and repos named by the caller."""
    write(root, "FLEET.md", fleet_md)
    reg = root / ".fleet"
    reg.mkdir(exist_ok=True)
    if overlay is not None:
        write(root, ".fleet/CHECKS.yaml", overlay)
    if checkers is not None:
        write(root, ".fleet/checkers.py", checkers)
    return root


class Configured(unittest.TestCase):
    """configure() binds every module global from FLEET.md; each test rebinds
    from a fixture and tearDown restores what the import-time call found."""
    def setUp(self):
        self.saved = (audit.ROOT, audit.FAMILY, audit.REGISTER, audit.TEMPLATE,
                      dict(audit.REPO_DIR), {k: set(v) for k, v in audit.GROUP_REPOS.items()})
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name).resolve()

    def tearDown(self):
        audit.ROOT, audit.FAMILY, audit.REGISTER, audit.TEMPLATE, dirs, groups = self.saved
        audit.REPO_DIR.clear(); audit.REPO_DIR.update(dirs)
        audit.GROUP_REPOS.clear(); audit.GROUP_REPOS.update(groups)
        audit._OVERLAY_LOADED.clear()
        self.tmp.cleanup()

    FLEET = """# Fleet
## Fleet

- name: fx
- org: acme
- template: tpl
- register: .fleet/ # a trailing comment must not reach the path

## Groups

- apps: the apps
- infra: deployments

## Repos

### tpl

- group: template
- port: 33099

### alpha

- group: apps
- path: "apps/alpha" # quoted, nested

### tf

- group: infra

### parked

- group: none

### blank

- group:

### escapee

- group: apps
- path: ../outside

### ../evil

- group: apps

```markdown
### fenced

- group: apps
```
"""

    def test_read_fleet_and_configure(self):
        fleet_fixture(self.root, self.FLEET)
        for name in ("tpl", "apps/alpha", "tf", "parked", "blank"):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        with contextlib.redirect_stderr(io.StringIO()) as err:
            audit.configure(self.root)
        self.assertEqual(audit.ROOT, self.root)
        self.assertEqual(audit.REGISTER, self.root / ".fleet")
        self.assertEqual(audit.TEMPLATE, "tpl")
        self.assertEqual(audit.FAMILY, ("tpl", "alpha", "tf"), "none, blank, escapee, ../evil and fenced are out")
        self.assertEqual(audit.REPO_DIR["alpha"], self.root / "apps" / "alpha", "path: honoured, quotes and comment stripped")
        self.assertEqual(audit.GROUP_REPOS, {"template": {"tpl"}, "apps": {"alpha"}, "infra": {"tf"}})
        self.assertIn("skipping 'escapee'", err.getvalue())
        self.assertIn("skipping '../evil'", err.getvalue())
        self.assertEqual(audit.repo_path("alpha"), self.root / "apps" / "alpha")

    def test_fleet_root(self):
        fleet_fixture(self.root, "## Fleet\n- name: fx\n")
        inner = self.root / "repo" / "sub"
        inner.mkdir(parents=True)
        self.assertEqual(audit.fleet_root(inner), self.root)
        write(self.root, "HERO.md", "# HERO\n")
        self.assertIsNone(audit.fleet_root(inner), "FLEET.md beside HERO.md is a repo, not a fleet")

    def test_missing_register_is_an_error(self):
        write(self.root, "FLEET.md", "## Fleet\n- name: fx\n- register: .flet/\n## Repos\n### a\n- group: apps\n")
        (self.root / "a").mkdir()
        with self.assertRaises(SystemExit) as cm:
            audit.configure(self.root)
        self.assertIn("register checkout missing", str(cm.exception))

    def test_register_must_stay_inside(self):
        write(self.root, "FLEET.md", "## Fleet\n- name: fx\n- register: ../elsewhere\n")
        with self.assertRaises(SystemExit) as cm:
            audit.configure(self.root)
        self.assertIn("outside the fleet", str(cm.exception))

    def test_explicit_fleet_without_fleet_md(self):
        with self.assertRaises(SystemExit):
            audit.configure(self.root)

    def test_lone_repo(self):
        r = git_repo(self.root, "solo")
        cwd = os.getcwd()
        try:
            os.chdir(r)
            audit.configure(None)
        finally:
            os.chdir(cwd)
        self.assertIsNone(audit.REGISTER)
        self.assertEqual(audit.FAMILY, ("solo",))
        self.assertEqual(audit.REPO_DIR["solo"], r.resolve())


class Register(unittest.TestCase):
    """load_register merges baseline + overlay by id and validates the
    RESULT: an overlay may add fields and records, never re-parent a check,
    hide a duplicate, or use a severity --fail-on would never match."""
    BASE = "\n".join([
        "controls:", "- id: C-A", "  title: A", "  severity: high", "  intent: a",
        "checks:", "- id: A-1", "  control: C-A", "  scope: repo", "  title: one", "  severity: low",
        "  detect: {method: manual}", ""])

    def setUp(self):
        self.saved = (audit.BASELINE, audit.REGISTER, {k: set(v) for k, v in audit.GROUP_REPOS.items()})
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "base").mkdir(); (self.root / "over").mkdir()
        write(self.root, "base/CONTROLS.yaml", self.BASE.split("checks:")[0])
        write(self.root, "base/CHECKS.yaml", "checks:" + self.BASE.split("checks:")[1])
        audit.BASELINE = self.root / "base"
        audit.REGISTER = self.root / "over"
        audit.GROUP_REPOS.clear()

    def tearDown(self):
        audit.BASELINE, audit.REGISTER, groups = self.saved
        audit.GROUP_REPOS.clear(); audit.GROUP_REPOS.update(groups)
        self.tmp.cleanup()

    def load(self, overlay_checks="", overlay_controls=""):
        if overlay_checks:
            write(self.root, "over/CHECKS.yaml", overlay_checks)
        if overlay_controls:
            write(self.root, "over/CONTROLS.yaml", overlay_controls)
        with contextlib.redirect_stderr(io.StringIO()):
            return audit.load_register()

    def test_overlay_fields_win_and_records_add(self):
        ctrl, checks = self.load(
            "checks:\n- id: A-1\n  severity: low\n"
            "- id: A-2\n  control: C-A\n  scope: ci\n  title: two\n  detect: {method: manual}\n")
        by = {k["id"]: k for k in checks}
        self.assertEqual(by["A-1"]["severity"], "low")
        self.assertEqual(by["A-1"]["title"], "one", "baseline field survives an overlay that did not set it")
        self.assertEqual(by["A-2"]["control"], "C-A")

    def test_a_check_may_not_name_a_repo(self):
        """Rejected, not ignored: dropping the field silently would leave an
        overlay author believing an exemption is in force while every repo in
        it is audited."""
        for field in ("reference: alpha", "known_violations: [alpha]"):
            with self.subTest(field=field):
                with self.assertRaises(SystemExit) as cm:
                    self.load(f"checks:\n- id: A-1\n  {field}\n")
                self.assertIn("retired", str(cm.exception))

    def test_no_overlay_files_is_baseline(self):
        ctrl, checks = self.load()
        self.assertEqual([k["id"] for k in checks], ["A-1"])

    def test_reparenting_rejected(self):
        with self.assertRaises(SystemExit) as cm:
            self.load("checks:\n- id: A-1\n  control: C-B\n", "controls:\n- id: C-B\n  title: B\n  severity: low\n  intent: b\n")
        self.assertIn("re-parent", str(cm.exception))

    def test_duplicate_id_rejected(self):
        with self.assertRaises(SystemExit) as cm:
            self.load("checks:\n- id: A-1\n  title: x\n- id: A-1\n  title: y\n")
        self.assertIn("duplicate", str(cm.exception))

    def test_bad_severity_rejected(self):
        with self.assertRaises(SystemExit) as cm:
            self.load("checks:\n- id: A-1\n  severity: High\n")
        self.assertIn("severity", str(cm.exception))

    def test_orphan_and_untested(self):
        with self.assertRaises(SystemExit):
            self.load("checks:\n- id: A-9\n  control: C-Z\n  scope: repo\n  title: z\n")
        with self.assertRaises(SystemExit):
            self.load("", "controls:\n- id: C-Q\n  title: Q\n  severity: low\n  intent: q\n")

    def test_malformed_yaml_names_the_file(self):
        with self.assertRaises(SystemExit) as cm:
            self.load("checks: [\n")
        self.assertIn("CHECKS.yaml", str(cm.exception))

    def test_applies_to_unknown_name_rejected_inside_a_fleet(self):
        audit.GROUP_REPOS.update({"apps": {"a"}})
        with self.assertRaises(SystemExit) as cm:
            self.load("checks:\n- id: A-1\n  applies_to: [aps]\n")
        self.assertIn("neither a FLEET.md group", str(cm.exception))
        ctrl, checks = self.load("checks:\n- id: A-1\n  applies_to: [Apps, go]\n")
        self.assertTrue(audit.applies(checks[0], "a"), "group names are case-insensitive")


class JsonOutput(unittest.TestCase):
    """The --json contract wayfare's compliance stage parses: one object per
    FAIL or ERROR cell on stdout, nothing else there, summary on stderr."""
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d).resolve()
            fleet_fixture(root, "## Fleet\n- name: fx\n## Repos\n### a\n- group: apps\n",
                          overlay="checks:\n- id: CI-02\n  applies_to: [apps]\n",
                          checkers="from audit import check, FAIL\n@check('ZZ-1')\ndef _(r):\n    raise RuntimeError('boom')\n")
            write(root, ".fleet/CONTROLS.yaml", "controls:\n- id: C-ZZ\n  title: z\n  severity: low\n  intent: z\n")
            write(root, ".fleet/CHECKS.yaml", "checks:\n- id: CI-02\n  applies_to: [apps]\n  example: |\n    version: 2\n- id: ZZ-1\n  control: C-ZZ\n  scope: repo\n  title: boom\n")
            git_repo(root, "a")
            p = subprocess.run([sys.executable, str(HERE / "audit.py"), "--fleet", str(root), "--no-snapshot", "--json", "--repo", "a"],
                               capture_output=True, text=True, env=CLEAN_ENV)
            lines = [json.loads(l) for l in p.stdout.splitlines() if l.strip()]
            self.assertTrue(lines, p.stderr)
            by = {(o["check"], o["status"]): o for o in lines}
            self.assertIn(("CI-02", "FAIL"), by, "no dependabot.yml in the fixture")
            self.assertEqual(by[("CI-02", "FAIL")]["example"], "version: 2\n",
                             "the correct shape travels with the finding, not a repo name")
            self.assertEqual(by[("CI-02", "FAIL")]["repo"], "a")
            self.assertIn(("ZZ-1", "ERROR"), by, "a raised checker is on stdout, flagged")
            self.assertIn("failing (check x repo)", p.stderr, "summary went to stderr")
            self.assertEqual(p.returncode, 2, "a checker error exits 2")

    def test_repo_dot_resolves_the_row(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d).resolve()
            fleet_fixture(root, "## Fleet\n- name: fx\n## Repos\n### svc\n- group: apps\n- path: services/svc\n", overlay="checks: []\n")
            (root / "services").mkdir()
            r = git_repo(root / "services", "svc")
            p = subprocess.run([sys.executable, str(HERE / "audit.py"), "--fleet", str(root), "--no-snapshot", "--repo", "."],
                               capture_output=True, text=True, cwd=r, env=CLEAN_ENV)
            self.assertIn("across 1 repos", p.stdout + p.stderr)
            p = subprocess.run([sys.executable, str(HERE / "audit.py"), "--fleet", str(root), "--no-snapshot", "--repo", "svc-typo"],
                               capture_output=True, text=True, cwd=r, env=CLEAN_ENV)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("not a FLEET.md row", p.stderr)


class IdeFloor(unittest.TestCase):
    def test_floor_and_gitignore_note(self):
        with tempfile.TemporaryDirectory() as d:
            r = git_repo(pathlib.Path(d), "fx")
            write(r, "lib/go.mod", "module x\n")
            write(r, ".vscode/extensions.json", '{\n  // jsonc\n  "recommendations": []\n}\n')
            git(r, "add", "-A")
            st, detail = audit.CHECKS["IDE-01"](r)
            self.assertEqual((st, detail), (audit.FAIL, "missing golang.go johnpapa.vscode-cloak redhat.vscode-yaml"))
            git(r, "rm", "-q", "--cached", ".vscode/extensions.json")
            write(r, ".gitignore", ".vscode/\n")
            st, detail = audit.CHECKS["IDE-01"](r)
            self.assertEqual(st, audit.FAIL)
            self.assertTrue(detail.endswith("excludes the .vscode/ directory"), detail)


class DenyAnchoring(unittest.TestCase):
    def test_cwd_relative_deny_does_not_count(self):
        with tempfile.TemporaryDirectory() as d:
            r = pathlib.Path(d)
            (r / "schema" / "gen").mkdir(parents=True)
            write(r, ".claude/settings.json", '{"permissions": {"deny": ["Read(./schema/gen/**)"]}}')
            st, detail = audit.CHECKS["STRUCT-11"](r)
            self.assertEqual(st, audit.FAIL)
            self.assertIn("cwd-relative", detail)
            write(r, ".claude/settings.json", '{"permissions": {"deny": ["Read(/schema/gen/**)"]}}')
            self.assertEqual(audit.CHECKS["STRUCT-11"](r), (audit.PASS, ""))


class Runner(unittest.TestCase):
    def test_bad_status_is_error(self):
        audit.CHECKS["ZZ-00"] = lambda r: ("pass", "")
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                rows, fails, errors = audit.run_matrix([{"id": "ZZ-00", "control": "C"}], ["hero-template"])
        finally:
            del audit.CHECKS["ZZ-00"]
        self.assertEqual(rows[0][1][0][0], audit.ERROR)
        self.assertEqual(len(errors), 1)
        self.assertEqual(fails, [])


if __name__ == "__main__":
    unittest.main()
