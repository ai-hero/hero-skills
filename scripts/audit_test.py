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
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("audit", HERE / "audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def write(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


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
        git_repo(self.root, "hero-template")

    def tearDown(self):
        audit.ROOT, audit.FAMILY, saved_dirs = self.saved
        audit.REPO_DIR.clear()
        audit.REPO_DIR.update(saved_dirs)
        self.tmp.cleanup()

    def worktrees(self):
        out = subprocess.run(["git", "worktree", "list"], cwd=self.root / "hero-template",
                             capture_output=True, text=True).stdout
        return out.strip().splitlines()

    def test_cleanup_on_exception(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(RuntimeError):
                with audit.snapshot_family("HEAD"):
                    self.assertNotEqual(audit.repo_path("hero-template"), self.root / "hero-template")
                    self.assertEqual(audit.repo_path("hero-template").name, "hero-template")
                    raise RuntimeError("boom")
        self.assertEqual(audit.REPO_PATH, {})
        self.assertEqual(audit._FLEET, {})
        self.assertEqual(len(self.worktrees()), 1)

    def test_unknown_ref_audits_checkout(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with audit.snapshot_family("no-such-ref"):
                self.assertEqual(audit.repo_path("hero-template"), self.root / "hero-template")
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
