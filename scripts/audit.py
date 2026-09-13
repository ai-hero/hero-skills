#!/usr/bin/env python3
# Copyright (c) 2026 A.I. Hero, Inc.
# All Rights Reserved.

"""Compute (check x repo) results for the harness compliance DB.

Three levels, and this script owns the third:

    control  — CONTROLS.yaml. What we want complied with.
    check    — CHECKS.yaml. A checklist item testing FOR a control. One
               control has several, possibly at different scopes: a `ui`
               check and a `backend` check can both prove C-TOOLCHAIN.
    result   — computed HERE, live, per (check x repo). Never stored: a
               stored result is a copy, and copies drift.

Checks with no implemented checker report MANUAL, never PASS — a check
nothing verifies must not masquerade as one that passed. Referential
integrity is enforced on load: a check naming an unknown control, or a
control that no check tests, is a hard error.

Usage:
    scripts/audit.py                        # every repo, every check
    scripts/audit.py --repo auth            # one repo
    scripts/audit.py --control C-HEALTH     # every check under a control
    scripts/audit.py --control CI-01        # one specific check
    scripts/audit.py --md                   # markdown table
    scripts/audit.py --fail-on high         # non-zero exit for CI

Where things live: the ENGINE and a generic BASELINE register ship with
hero-skills (this file, assets/compliance/); the fleet's own OVERLAY — its
reference repos, its incident history, its known_violations — lives in the
fleet folder's register checkout, named by FLEET.md's `register:` key
(default .fleet/). The two are merged by id, overlay winning. Run inside a
fleet (any checkout below a FLEET.md) and the family is FLEET.md's rows
whose group is not `none`; run anywhere else and the family is the current
repo alone, baseline only. --fleet PATH names the fleet root explicitly.

Each repo is audited at --ref (default origin/main) in a detached worktree,
not at whatever branch the checkout sits on; --no-snapshot audits the
checkouts as they sit.
"""

import argparse
import contextlib
import json
from datetime import datetime
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

try:
    import yaml
except ImportError:
    sys.exit("pyyaml required: pip install pyyaml")

HERE = pathlib.Path(__file__).resolve().parent.parent   # the hero-skills plugin
BASELINE = HERE / "assets" / "compliance"               # generic register, public
# Set by configure(): the fleet root (or the lone repo's parent), the fleet's
# register overlay directory (None outside a fleet), the template repo's row
# name (None outside a fleet), and each family repo's directory.
ROOT = None
REGISTER = None
TEMPLATE = None
REPO_DIR = {}

PASS, FAIL, NA, MANUAL, ERROR = "PASS", "FAIL", "n/a", "MANUAL", "ERROR"
STATUSES = {PASS, FAIL, NA, MANUAL, ERROR}

# The repos this register governs. Explicit, and it has to be — but the
# decision is FLEET.md's, not this file's: a row whose group is not `none` is
# in, and configure() fills FAMILY from it. Outside a fleet the family is the
# one repo this runs in.
#
# The old rule was "every sibling checkout with a CLAUDE.md", which answers a
# different question: plenty of repos in this workspace have one and are not
# part of the family. saga is the proof — it has a CLAUDE.md and its own
# client-side OAuth, so under the heuristic its OAuth env names counted as
# fleet evidence in AUTH-01's cross-repo comparison. AUTH-01 could then never
# go green no matter what these five repos did, because a repo nobody here
# governs disagreed. A check that cannot be satisfied is a check people learn
# to ignore, which kills a register the same way a false PASS does — just from
# the other end.
#
# Membership is a decision, not something to sniff for. Adding a repo here
# means committing to hold it to every check in CHECKS.yaml.
# hero-skills earns membership by a different route than the rest: it ships no
# product, but CI-03 and CI-04 name it as `reference`, so the register asserts
# the fleet's approval gate is enforced THERE. Leaving it outside FAMILY took
# the benefit of that claim without the commitment — if its shared workflow
# dropped the author gate, every caller would still report PASS. It is also
# the one repo whose default branch publishes to all the others.
FAMILY = ()

# The register's own files, repo-relative. A content check that greps for a
# banned string finds these first: they have to spell what they ban. Excluding
# them is not special-pleading — it is the difference between the map and the
# territory.
REGISTER_FILES = ("CONTROLS.yaml", "CHECKS.yaml", "scripts/audit.py")

# name -> the tree actually audited: a detached worktree of --ref while
# snapshot_family() is live, else the checkout as it sits. The register audits
# what is MERGED, not what is checked out — a sibling mid-branch with an agent
# in it is not the fleet's state — so a checker that looks across the family
# goes through repo_path(), never ROOT / name.
REPO_PATH = {}


def repo_path(name):
    return REPO_PATH.get(name, REPO_DIR.get(name, ROOT / name))


def fleet_root(start=None):
    """The nearest ancestor holding FLEET.md without HERO.md, or None. Same
    rule as hero_fleet_root in hero-lib.sh: a FLEET.md beside a HERO.md is a
    committed copy inside a repo, and is passed over."""
    d = pathlib.Path(start or os.getcwd()).resolve()
    while True:
        if (d / "FLEET.md").is_file() and not (d / "HERO.md").is_file():
            return d
        if d.parent == d:
            return None
        d = d.parent


def read_fleet(root):
    """FLEET.md's `## Fleet` keys and `## Repos` rows, mirroring hero-lib's
    hero_fleet_field / hero_fleet_repos. Fenced blocks are skipped and a
    trailing `# comment` is stripped from every value."""
    fields, repos, sec, cur, fence = {}, [], None, None, False
    for line in (root / "FLEET.md").read_text().splitlines():
        if line.startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        if line.startswith("## "):
            sec, cur = line[3:].strip(), None
            continue
        if sec == "Repos" and line.startswith("### "):
            cur = {"name": line[4:].strip(), "group": "none", "path": "", "port": ""}
            repos.append(cur)
            continue
        m = re.match(r"^- ([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), re.sub(r"\s+#.*$", "", m.group(2)).strip().strip("\"'")
        if sec == "Fleet":
            fields[key] = val
        elif sec == "Repos" and cur is not None and key in cur:
            cur[key] = val.lower() if key == "group" else val
    return fields, repos


def configure(root=None):
    """Bind ROOT, FAMILY, REGISTER, TEMPLATE and REPO_DIR — from FLEET.md when
    inside a fleet, else from the current repo alone. Called by main() and by
    consistency.py; the import-time call below makes the module usable from
    tests without one."""
    global ROOT, FAMILY, REGISTER, TEMPLATE
    root = pathlib.Path(root).resolve() if root else fleet_root()
    REPO_DIR.clear()
    if root is None:
        rc, top = sh(pathlib.Path.cwd(), "git rev-parse --show-toplevel")
        repo = pathlib.Path(top.strip()) if rc == 0 and top.strip() else pathlib.Path.cwd()
        ROOT, FAMILY, REGISTER, TEMPLATE = repo.parent, (repo.name,), None, None
        REPO_DIR[repo.name] = repo
        return
    fields, repos = read_fleet(root)
    ROOT = root
    reg = fields.get("register") or ".fleet/"
    REGISTER = (root / reg.rstrip("/")).resolve()
    TEMPLATE = fields.get("template") or None
    names = []
    for row in repos:
        if row["group"] == "none":
            continue
        path = (root / (row["path"] or row["name"])).resolve()
        # A row whose path escapes the fleet is not this fleet's repo, whatever
        # its name says; hero_fleet_repos skips it for the same reason.
        if root not in path.parents:
            continue
        REPO_DIR[row["name"]] = path
        names.append(row["name"])
    FAMILY = tuple(names)


def sh(cwd, cmd):
    """Run a shell command, return (rc, stdout). Never raises."""
    try:
        # dev tooling; cmd is a hardcoded pipeline from CONTROLS.yaml, or interpolates
        # only regex-pinned tokens (ARCH-02: 40 hex chars) — never raw external input
        p = subprocess.run(
            cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=60  # nosemgrep: python.lang.security.audit.subprocess-shell-true.subprocess-shell-true
        )
        return p.returncode, p.stdout.strip()
    except Exception:
        return 1, ""


def sh3(cwd, cmd):
    """sh() with stderr. Raises on the failure classes sh() hides (timeout,
    missing cwd) so a caller inside run_matrix reports ERROR, never PASS."""
    p = subprocess.run(
        cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=60  # nosemgrep: python.lang.security.audit.subprocess-shell-true.subprocess-shell-true
    )
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def tracked(repo, *pathspecs):
    """Tracked paths matching the pathspecs. A failed `git ls-files` raises:
    an empty listing from a command that did not run is not a clean repo."""
    rc, out, err = sh3(repo, "git ls-files -- " + " ".join(shlex.quote(x) for x in pathspecs))
    if rc:
        raise RuntimeError(f"git ls-files failed in {repo.name}: {err or f'rc={rc}'}")
    return out.splitlines()


def uncommented(text):
    """Strip YAML comments so a checker can't match the prose ABOUT a bug
    and report it as the bug.

    Learned the hard way: GATE-02 greps for the invalid v1 spelling
    `shadow: true`, and hero-template's .golangci.yaml has a header comment
    warning that that spelling silently does nothing. The checker matched
    the warning and failed the one config in the fleet that is correct. A
    false FAIL is as corrosive as a false PASS — it trains you to ignore
    the report.
    """
    out = []
    for line in text.splitlines():
        s = line.split("#", 1)[0] if not line.lstrip().startswith("#") else ""
        out.append(s)
    return "\n".join(out)


def yml(repo, stem):
    """Resolve a YAML path by stem, accepting either extension.

    PLACE-06 moves the fleet from .yml to .yaml, and the repos convert one at
    a time. A checker that hardcodes either extension breaks every repo on the
    other side of the migration — so resolve by stem and let the repo be
    mid-flight. Prefers .yaml (the target) and falls back to .yml.
    """
    for ext in (".yaml", ".yml"):
        f = repo / f"{stem}{ext}"
        if f.is_file():
            return f
    return repo / f"{stem}.yaml"


def has_go(repo):
    return (repo / "go.work").exists() or any(repo.glob("*/go.mod"))


def has_node(repo):
    return (repo / "package.json").is_file() or (repo / "ui" / "package.json").is_file()


def has_python(repo):
    # A repo "contains Python" as a PRODUCT language — backend or research —
    # not as harness tooling. A pyproject/requirements marks a real project;
    # otherwise, tracked .py OUTSIDE scripts/ (this repo's own compliance
    # harness is Python and must not make every repo that copies it look like a
    # Python project) and outside vendored trees. git ls-files so node_modules
    # and a vendored mockup/ never count.
    if (repo / "pyproject.toml").is_file() or (repo / "requirements.txt").is_file():
        return True
    _rc, out = sh(repo, "git ls-files '*.py' | grep -vE 'node_modules/|/mockup/|^scripts/' | head -1")
    return bool(out.strip())


def precommit(repo):
    """Raw .pre-commit-config.yaml text, or "". Matched as text on purpose: the
    same tool appears under different hook ids across the fleet (ui-lint /
    eslint / eslint-taste), so the checks look for the TOOL signature, not a
    canonical id a repo has no reason to adopt."""
    f = repo / ".pre-commit-config.yaml"
    return f.read_text() if f.is_file() else ""


def _missing_hooks(repo, required):
    """required: {label: [substrings, any of which proves the tool runs]}.
    Returns the labels whose tool is absent from the pre-commit config."""
    text = precommit(repo)
    missing = []
    for label, needles in required.items():
        if not any(n in text for n in needles):
            missing.append(label)
    return missing


def has_ui(repo):
    """Does this repo ship a web front end at all?

    Every family repo used to be a product app, so ui/backend checks could
    assume the subsystem existed and report FAIL when they could not find it.
    hero-skills is a Claude Code plugin — no ui/, no package.json, no Go
    module — and under that assumption it failed AUTH-01, AUTH-02, UI-01 and
    STRUCT-03 for not having a version gate, OAuth vars and an .nvmrc it has
    no use for. That is the "check that cannot be satisfied" this register's
    own FAMILY comment warns kills a register. Absent subsystem is n/a, not a
    violation.
    """
    return (repo / "ui" / "src").is_dir() or (repo / "package.json").is_file()


def has_backend(repo):
    """Does this repo ship a service with HTTP endpoints? See has_ui."""
    return (repo / "go.mod").is_file() or (repo / "lib").is_dir() or (repo / "src").is_dir()


def _ships_image(repo):
    return bool(list(repo.glob("Dockerfile*")))


def workflows(repo):
    d = repo / ".github" / "workflows"
    return sorted(list(d.glob("*.yml")) + list(d.glob("*.yaml"))) if d.is_dir() else []


def own_port(repo):
    """The repo's own family port = the compose dev default. That file is
    what actually binds, so it is the source of truth; everything else is
    derived (PORT-02)."""
    f = yml(repo, "docker-compose.dev")
    if not f.is_file():
        return None
    m = re.search(r"HOST_PORT:-(\d{4,5})", f.read_text())
    return m.group(1) if m else None


# Each checker returns (status, detail). Keyed by control id.
CHECKS = {}


def check(cid):
    def deco(fn):
        CHECKS[cid] = fn
        return fn

    return deco


@check("STRUCT-01")
def _(r):
    if not list(r.glob("Dockerfile*")):
        return NA, "no Dockerfile"
    return (PASS, "") if (r / ".dockerignore").is_file() else (FAIL, "missing")


@check("STRUCT-02")
def _(r):
    if not has_go(r):
        return NA, "no Go"
    return (PASS, "") if yml(r, ".golangci").is_file() else (FAIL, "missing")


@check("STRUCT-03")
def _(r):
    if not has_ui(r):
        return NA, "no UI"
    return (PASS, "") if (r / ".nvmrc").is_file() else (FAIL, "missing")


@check("STRUCT-04")
def _(r):
    pc = r / ".pre-commit-config.yaml"
    if not pc.is_file() or "detect-secrets" not in pc.read_text():
        return NA, "no detect-secrets"
    return (PASS, "") if (r / ".secrets.baseline").is_file() else (FAIL, "no baseline")


@check("STRUCT-05")
def _(r):
    # Read the COMMITTED .gitignore, not `git check-ignore`.
    #
    # check-ignore reports the effective state, which folds in
    # .git/info/exclude — a per-clone, unversioned file. Three repos here
    # carry `.claude/` in their local exclude, so check-ignore called this
    # a FAIL on this machine while the repo config was correct and would
    # behave correctly on any other clone or in CI. This control is about
    # what the repo ships, so read what the repo ships.
    f = r / ".gitignore"
    if not f.is_file():
        return FAIL, "no .gitignore"
    lines = [l.strip() for l in uncommented(f.read_text()).splitlines() if l.strip()]
    if ".claude/" in lines or ".claude" in lines:
        return FAIL, ".claude/ blanket-ignored — skills can never be committed"
    if not any(l.startswith(".claude/") for l in lines):
        return FAIL, "no .claude rule — local settings untracked only by luck"
    if "!.claude/skills/" not in lines:
        return FAIL, "skills not un-ignored"
    if ".claude/settings.local.json" not in lines:
        return FAIL, "settings.local.json not ignored"
    return PASS, "narrow rule"


@check("STRUCT-06")
def _(r):
    _rc, out = sh(r, r"git ls-files | grep -E '(^|/)\.DS_Store$|(^|/)Thumbs\.db$'")
    return (FAIL, f"{len(out.splitlines())} tracked") if out else (PASS, "")


@check("PLACE-01")
def _(r):
    _rc, out = sh(
        r,
        "find . -name 'Dockerfile*' -not -path '*/node_modules/*' "
        "-not -path './.git/*' -not -path './Dockerfile*' -not -path './.*'",
    )
    if not out:
        return PASS, "all Dockerfiles at root"
    # The rule allows a separately-scaled sidecar IF its escape from the root
    # .dockerignore is documented THERE. That is the condition that makes it
    # variance, and it is checkable: the root .dockerignore must name the
    # subfolder. Whether the sidecar also avoids `COPY . .` still needs a
    # human, so this reports MANUAL rather than PASS — a documented exception
    # should not go green unexamined, but nor should it stay permanently red
    # and train people to ignore the report.
    strays = [x.strip() for x in out.splitlines() if x.strip()]
    di = r / ".dockerignore"
    doc = di.read_text() if di.is_file() else ""
    undocumented = [x for x in strays
                    if x.split("/")[1] not in doc] if doc else strays
    if undocumented:
        return FAIL, "undocumented: " + " ".join(undocumented)
    return MANUAL, "documented sidecar: " + " ".join(strays) + " — re-verify it copies named files only"


@check("PLACE-02")
def _(r):
    return (FAIL, "bare docker-compose.yml") if (r / "docker-compose.yml").is_file() else (PASS, "")


def registry():
    """The family port table, DERIVED from each family repo's compose default.

    There is no registry file: the compose default is what actually binds,
    so it is the only thing that cannot lie. Scanning for it means the
    table is computed from reality rather than maintained by hand — which
    is why there is nothing to copy, and therefore nothing to drift
    (PORT-01).
    """
    out = {}
    for name in FAMILY:
        d = repo_path(name)
        if not (d / ".git").exists():
            continue
        p = own_port(d)
        if p:
            out[name] = p
    return out


@check("PORT-01")
def _(r):
    mine = own_port(r)
    if not mine:
        return NA, "no dev stack"
    # STRICT: any number in the 330xx family range that is not this repo's
    # own port is a violation. Matching only against the derived registry
    # was tried and under-reports badly — a repo whose own compose default
    # is wrong makes its intended port underivable, so its stale family
    # table slips through unnoticed. It also lets an unallocated family
    # number sit in an example, which is exactly the confusion the rule
    # exists to prevent: if a number is meant to be arbitrary, it must not
    # look like it came from the registry.
    owner = {p: n for n, p in registry().items()}
    # `git grep`, not `grep -r`: only TRACKED files are the repo. A plain
    # recursive grep also reads gitignored session scratch — .playwright-mcp
    # page dumps, .output, .data — and reported a port that appears inside a
    # UUID in a browser-automation artifact nobody committed.
    _rc, out = sh(
        r,
        "git grep -nI -E '330[0-9][0-9]' -- "
        "'*.md' 'Justfile' '*.yml' '*.yaml' '*.ts' 2>/dev/null",
    )
    found = {}
    for line in out.splitlines():
        # Alphanumeric boundaries, not just digit ones: `330\d\d` alone
        # matches five digits inside a longer token (a UUID, a git SHA) and
        # invents findings. Guarding only against digits is not enough —
        # a hex blob like "…cad33039" has a LETTER on the left.
        for p in re.findall(r"(?<![0-9A-Za-z])330\d\d(?![0-9A-Za-z])", line):
            if p != mine:
                found.setdefault(p, line.split(":")[0])
    if found:
        bits = [f"{p}({owner.get(p, 'unallocated')})" for p in sorted(found)]
        return FAIL, "knows " + ",".join(bits)
    return PASS, f"own {mine}"


@check("PORT-02")
def _(r):
    mine = own_port(r)
    if not mine:
        return NA, "no dev stack"
    ports = {mine}
    j = r / "Justfile"
    if j.is_file():
        ports |= set(re.findall(r"HOST_PORT:-(\d{4,5})", j.read_text()))
    if len(ports) > 1:
        return FAIL, "disagree: " + ",".join(sorted(ports))
    if not mine.startswith("330"):
        return FAIL, f"binds {mine}, not a family port"
    return PASS, mine


@check("HLT-01")
def _(r):
    if not has_backend(r):
        return NA, "no backend"
    _rc, out = sh(r, "grep -rl '/livez' lib ui/src src 2>/dev/null")
    _rc2, out2 = sh(r, "grep -rl '/readyz' lib ui/src src 2>/dev/null")
    if out and out2:
        return PASS, "/livez + /readyz"
    _rc3, legacy = sh(
        r, "grep -rhoE '/healthz/live|/healthz|/z/health|/api/health' lib ui/src src 2>/dev/null | sort -u"
    )
    return FAIL, (legacy.replace("\n", ",") or "no probes found")


@check("HLT-02")
def _(r):
    f = r / "Dockerfile.prod"
    if not f.is_file():
        return NA, "no Dockerfile.prod"
    # Parse the URL out of the HEALTHCHECK's own CMD, not the surrounding
    # prose. A looser regex matched "/readyz" from the comment ABOVE the
    # directive explaining why we do NOT probe it, and failed the one repo
    # that is correct — the same trap as grepping a config for the bug its
    # comment warns about.
    t = uncommented(f.read_text())
    i = t.find("HEALTHCHECK")
    if i < 0:
        return FAIL, "no HEALTHCHECK"
    # From the directive to the end; a Dockerfile has at most one HEALTHCHECK
    # and its CMD follows immediately. Matching the line itself is fiddly —
    # `[^\n]*` eats the trailing backslash, so the continuation never joins.
    u = re.search(r"https?://[^/\s'\"]+(/[A-Za-z0-9/_-]*)", t[i:])
    if not u:
        return MANUAL, "HEALTHCHECK present; could not parse the probed path"
    probe = u.group(1)
    if "livez" in probe:
        return PASS, probe
    if "readyz" in probe:
        # Unambiguous: readyz is readiness by definition.
        return FAIL, f"probes {probe} — readiness drives restarts"
    # Anything else needs a human. This control is about SEMANTICS — does the
    # probed endpoint check dependencies? — not about the path's name. Grepping
    # for "livez" made this a naming check wearing a safety check's clothes,
    # and it reported four false FAILs: auth's /z/health, hiro's /healthz and
    # website's + design-system's /api/health all return a static ok and probe
    # nothing, so none of them can drive a restart storm. Only the template
    # ever had the bug. A checker cannot read a Go handler, so say MANUAL
    # rather than guess from the spelling.
    return MANUAL, f"probes {probe} — verify it checks no dependencies"


@check("CI-01")
def _(r):
    wfs = workflows(r)
    if not wfs:
        return NA, "no workflows"
    bad = 0
    for w in wfs:
        for line in w.read_text().splitlines():
            if not re.search(r"^\s*(-\s*)?uses:", line):
                continue
            # A first-party ai-hero/* reusable WORKFLOW may ride `main` or a
            # v-tag — the CI-01 carve-out. Narrow on every axis:
            #   - only a reusable workflow, not a plain ai-hero action, which
            #     is no kind of fleet-wide distribution mechanism;
            #   - only `main`, the callee's PROTECTED default branch, never an
            #     arbitrary branch. @main is acceptable BECAUSE hero-skills
            #     gates main on review — approval required, stale approvals
            #     dismissed, last-push approval required. A feature branch is
            #     gated on nothing, and this caller hands the callee
            #     ANTHROPIC_API_KEY and pull-requests: write;
            #   - a v-tag stays permitted for repos not yet migrated.
            if re.search(
                r"uses:\s*ai-hero/[^/]+/\.github/workflows/[^@\s]+@(main|v[0-9][^\s]*)\s*(#.*)?$",
                line,
            ):
                continue
            if not re.search(r"@[0-9a-f]{40}", line):
                bad += 1
    return (FAIL, f"{bad} unpinned") if bad else (PASS, "")


@check("CI-02")
def _(r):
    return (PASS, "") if yml(r / ".github", "dependabot").is_file() else (FAIL, "missing")


@check("CI-14")
def _(r):
    f = yml(r / ".github", "dependabot")
    if not f.is_file():
        return NA, "no dependabot config"
    doc = yaml.safe_load(f.read_text()) or {}
    updates = doc.get("updates", []) or []
    if not updates:
        return FAIL, "no update entries"
    # Every ecosystem needs a catch-all group (patterns ["*"]) scoped to
    # minor+patch, so routine bumps land as one PR. Majors stay ungrouped on
    # purpose, so a group WITHOUT the update-types restriction does not count.
    ungrouped = []
    for u in updates:
        groups = (u.get("groups") or {}).values()
        ok = any(
            "*" in (g.get("patterns") or [])
            and {"minor", "patch"} <= set(g.get("update-types") or [])
            for g in groups
        )
        if not ok:
            ungrouped.append(u.get("package-ecosystem", "?"))
    if ungrouped:
        return FAIL, "no minor/patch catch-all group: " + ",".join(sorted(set(ungrouped)))
    return PASS, "each ecosystem groups minor+patch"


@check("CI-15")
def _(r):
    f = yml(r / ".github", "dependabot")
    if not f.is_file():
        return NA, "no dependabot config"
    doc = yaml.safe_load(f.read_text()) or {}
    updates = doc.get("updates", []) or []
    if not updates:
        return FAIL, "no update entries"
    # A quarantine window on version updates only — default-days is the option
    # every ecosystem supports (docker/actions support nothing finer). Security
    # updates for known advisories are exempt by design, so this does not slow a
    # real patch.
    missing = [
        u.get("package-ecosystem", "?")
        for u in updates
        if not (u.get("cooldown") or {}).get("default-days")
    ]
    if missing:
        return FAIL, "no cooldown: " + ",".join(sorted(set(missing)))
    return PASS, "each ecosystem quarantines new releases"


# ── template-lag helpers (TMPL-01) ──────────────────────────────────────────
# The template is the seed every clone starts from, so a dependency it pins
# OLDER than the fleet already runs ships that staleness — the x/crypto CVEs —
# into every future clone. These read the declared versions so the check can
# assert the template is not behind any consumer on a dependency they share.

def _semver(v):
    """Leading MAJOR.MINOR.PATCH as a tuple; strips a range operator (^ ~ >=),
    a leading v, and any pre-release/pseudo-version suffix. None when there is
    no MAJOR.MINOR.PATCH to read ("^18", "*", "workspace:*", a git URL).

    A None is SKIPPED, never guessed, so this never false-FLAGS a lag. The risk
    is the opposite direction: a None on the TEMPLATE side drops that dep from
    the comparison, so a real lag on it would be missed. Acceptable because the
    template pins exact versions (go.mod) and caret-with-patch ranges
    (package.json), both of which parse — a None there is itself the anomaly,
    and TMPL-01 turns an all-empty template map into MANUAL rather than PASS.
    Known blind spot: Go pseudo-versions (v0.0.0-<ts>-<hash>) all collapse to
    (0,0,0), so lag between two pseudo-versioned pins is invisible."""
    m = re.match(r"[\^~>=<\s]*v?(\d+)\.(\d+)\.(\d+)", (v or "").strip())
    return tuple(int(x) for x in m.groups()) if m else None


def _go_versions(repo):
    """{module_path: highest declared version tuple} across every go.mod. An
    unreadable go.mod is skipped, not raised — one bad sibling must not sink the
    whole cross-repo comparison (it would degrade TMPL-01 to MANUAL and hide a
    real lag against the healthy consumers)."""
    deps = {}
    for gomod in repo.glob("*/go.mod"):
        try:
            text = gomod.read_text()
        except OSError:
            continue
        for line in text.splitlines():
            m = re.match(r"\s*([\w.\-]+/[\w./\-]+)\s+(v\d\S*)", line)
            if not m:
                continue
            t = _semver(m.group(2))
            if t and t > deps.get(m.group(1), ()):
                deps[m.group(1)] = t
    return deps


def _npm_versions(repo):
    """{package: highest declared version tuple} from root and ui package.json."""
    deps = {}
    for pj in (repo / "package.json", repo / "ui" / "package.json"):
        if not pj.is_file():
            continue
        try:
            doc = json.loads(pj.read_text())
        except Exception:
            continue
        for section in ("dependencies", "devDependencies"):
            for name, spec in (doc.get(section) or {}).items():
                t = _semver(spec)
                if t and t > deps.get(name, ()):
                    deps[name] = t
    return deps


# A floating spec resolves to whatever is newest AT INSTALL TIME, never
# pinned to anything this repo committed to. `_semver()` correctly returns
# None for these (skip-don't-guess is right — TMPL-01 must not fabricate a
# version to compare), but None is also the return value for a workspace
# protocol or a git URL pinned to a full commit SHA, both legitimate.
#
# An earlier version of this function enumerated the dangerous shapes as a
# closed tuple of literal strings ("latest", "next", "canary", "*"). That
# reproduces, one level down, the exact defect this check exists to catch:
# npm dist-tags are not a fixed vocabulary, so a spec pinned to any OTHER
# tag name (beta, rc, alpha, insiders, nightly, ...) bypassed it silently —
# and a git dependency pinned to a floating BRANCH ref (not a commit SHA)
# has the identical "different tree on every install" risk profile as
# "latest", yet the enumeration exempted every git URL alike, pinned or not.
# Classify structurally instead: floating iff the spec names no version AND
# isn't one of the recognized versionless-but-genuinely-pinned protocols.
def _is_floating_npm_spec(spec):
    s = str(spec).strip()
    # `npm:<pkg>@<range>` aliases another package under a different import
    # name — the alias itself pins nothing; whatever floats or doesn't is the
    # WRAPPED range. The wrapped package name may itself contain "@" (a scope,
    # "npm:@scope/pkg@^1.0.0"), so split on the LAST "@", not the first. No
    # "@" at all (or only the scope's) means the alias names no version,
    # which resolves at install time exactly like a bare dist-tag — floats.
    if s.startswith("npm:"):
        aliased = s[len("npm:"):]
        at = aliased.rfind("@")
        return _is_floating_npm_spec(aliased[at + 1 :]) if at > 0 else True
    # `>=`/`>` with no paired `<`/`<=` anywhere in the spec has no ceiling —
    # "resolves to whatever is newest at install time" is exactly the risk
    # this check exists to catch, even though (unlike a bare tag) it names a
    # digit and so used to pass the `_semver()` short-circuit below un-flagged
    # (">=0.0.0" parses to a real (0, 0, 0) tuple, which reads as "pinned").
    if re.match(r"^>=?\s*\d", s) and "<" not in s:
        return True
    if _semver(s) is not None:
        return False
    if s.startswith(("workspace:", "file:", "link:")):
        return False
    if re.search(r"#[0-9a-f]{40}$", s):
        return False  # git URL pinned to a full commit SHA
    # `(?:[\w-]+:)?` optionally matches the shorthand's host prefix
    # (github:, gitlab:, bitbucket:) before owner/repo#ref — without it, a
    # tag ref containing a digit ("github:owner/repo#v1.2.3") fell through
    # to the digit check below and was misread as a bounded version, when a
    # git tag is no more immutable than a branch: either can be repointed.
    if s.startswith(("git+", "git://")) or re.match(r"^(?:[\w-]+:)?[\w.-]+/[\w.-]+#", s):
        return True  # git URL/shorthand with no SHA pin — a branch/tag, floats
    # _semver() only recognizes a FULL MAJOR.MINOR.PATCH, so a caret/tilde
    # range with fewer components ("^4", "~19", "4.x") returned None above —
    # but "^4" is bounded to major 4 exactly as surely as "^4.0.0" is; it is
    # not floating. The first cut of this function used that None as "treat
    # as potentially floating," which misfired on every partial-range spec
    # already in real use in this family (tailwindcss "^4", eslint "^10",
    # typescript "^5", @types/react "^19"). The actual dividing line a
    # floating spec crosses is having NO version number in it at all — a bare
    # dist-tag (latest, beta, rc, nightly, ...) or the wildcard are pure words;
    # any range, however partial or open-ended, still names a digit.
    if re.search(r"\d", s):
        return False
    # No digits anywhere: a bare tag/word, the wildcard "*", or an empty
    # string — npm's own alternate spelling of "*" — all float.
    return True


def _floating_npm_deps(repo):
    """{package: raw spec} for every dependency pinned to a floating spec, in
    root and ui package.json.

    A malformed package.json is let propagate rather than caught here — this
    mirrors TMPL-01's own reasoning for the same two files: a read failure on
    the very manifest this check protects must not report as PASS just
    because a JSON error was swallowed one function up. The check-runner in
    main() already turns any propagated exception into MANUAL with the error
    text, which is the correct outcome for "could not read this repo's
    dependencies" — silently returning {} here would collapse that into a
    fabricated, wrong PASS instead."""
    out = {}
    for pj in (repo / "package.json", repo / "ui" / "package.json"):
        if not pj.is_file():
            continue
        doc = json.loads(pj.read_text())
        for section in ("dependencies", "devDependencies"):
            for name, spec in (doc.get(section) or {}).items():
                if _is_floating_npm_spec(spec):
                    out[name] = spec
    return out


@check("TMPL-01")
def _(r):
    # Only the template is judged — it is the seed. A consumer being ahead is
    # the normal, expected state (it is where a bump is proven first); the bug
    # is the template STAYING behind, so the fix is always a backport into it.
    if r.name != "hero-template":
        return NA, "not the template"
    tg, tn = _go_versions(r), _npm_versions(r)
    # The seed always has Go modules and a ui/package.json with deps. An empty
    # map means its OWN manifest did not parse — surface MANUAL rather than
    # compare consumers against nothing and report a false-green PASS (the very
    # file whose staleness this check guards is the one that failed to read).
    if (list(r.glob("*/go.mod")) and not tg) or (
        (r / "ui" / "package.json").is_file() and not tn
    ):
        return MANUAL, "could not read the template's own go.mod / package.json deps"
    behind = []
    for name in FAMILY:
        if name == "hero-template":
            continue
        cr = repo_path(name)
        if not cr.is_dir():
            continue
        for dep, cv in _go_versions(cr).items():
            if dep in tg and cv > tg[dep]:
                behind.append(f"{dep}<{name}")
        for dep, cv in _npm_versions(cr).items():
            if dep in tn and cv > tn[dep]:
                behind.append(f"{dep}<{name}")
    if behind:
        uniq = sorted(set(behind))
        return FAIL, f"{len(uniq)} shared deps behind a consumer: " + ", ".join(uniq[:6])
    return PASS, "not behind any consumer on a shared dep"


@check("CI-16")
def _(r):
    if not has_node(r):
        return NA, "no package.json"
    floating = _floating_npm_deps(r)
    if not floating:
        return PASS, "no floating npm tags"
    names = sorted(floating)
    return FAIL, f"{len(names)} floating tag(s): " + ", ".join(names[:6])


# GitHub runs auto-approve.yaml AND auto-approve.yml if both exist, so a check
# that resolves ONE of them (yml()) can pass a gated .yaml while an ungated
# .yml approves PRs beside it. A half-finished PLACE-06 rename leaves exactly
# that state. Anything asserting a property of "the auto-approve workflow"
# has to mean every file GitHub would run.
def _approve_workflows(r):
    return [w for w in workflows(r) if w.stem == "auto-approve"]


# Delegation to the shared workflow. A v-tag OR a full SHA both count: several
# repos pin the SHA, which is stricter than the tag, and demanding the tag
# would fail them for being MORE careful. A branch ref counts as neither.
# `ya?ml` because the CALLEE's filename is hero-skills' business and PLACE-06
# is moving the fleet off .yml — hardcoding it would flip every caller to FAIL
# the day hero-skills renames its own file.
_DELEGATES = re.compile(
    r"ai-hero/hero-skills/\.github/workflows/auto-approve\.ya?ml@"
    r"(main|v[0-9][^\s]*|[0-9a-f]{40})"
)


def _jobs(path):
    try:
        doc = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError:
        return None
    return (doc.get("jobs") or {}) if isinstance(doc, dict) else {}


@check("CI-03")
def _(r):
    wfs = _approve_workflows(r)
    if not wfs:
        return NA, "no auto-approve"
    # Parse, don't substring-match. Against raw text, `author_association`
    # anywhere in the file counted as a gate: an inline trailing comment
    # ("# author_association gate dropped, see #123"), a gate on a DIFFERENT
    # job than the one that approves, or an inverted comparison all passed
    # while nothing was actually gated.
    ungated = []
    for w in wfs:
        jobs = _jobs(w)
        if jobs is None:
            return FAIL, f"{w.name} does not parse"
        for name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            cond = str(job.get("if", ""))
            if cond.strip() == "false":  # disabled job cannot approve
                continue
            if _DELEGATES.search(str(job.get("uses", ""))):
                continue
            # Both spellings are in use and both are correct: an `==` chain,
            # and `contains(fromJSON('["OWNER",…]'), …author_association)`.
            # Requiring `==` failed the second, which is the better form.
            # Reject only an outright inversion, which gates on nothing.
            if "author_association" in cond and not re.search(
                r"author_association\s*!=", cond
            ):
                continue
            ungated.append(f"{w.name}:{name}")
    if ungated:
        return FAIL, "ungated: " + ", ".join(ungated[:3])
    return PASS, ""


@check("CI-04")
def _(r):
    wfs = _approve_workflows(r)
    if not wfs:
        return NA, "no auto-approve"
    for w in wfs:
        if "Could not get review from Claude" in w.read_text():
            return FAIL, "fails OPEN"
    # A thin caller holds no API call, so the fail-open string can never
    # appear in it — returning PASS would be asserting a property of a file in
    # ANOTHER repo that this audit cannot see. The docstring's rule applies:
    # a check nothing verifies must not masquerade as one that passed.
    jobs = {}
    for w in wfs:
        jobs.update(_jobs(w) or {})
    if any(
        _DELEGATES.search(str(j.get("uses", "")))
        for j in jobs.values()
        if isinstance(j, dict)
    ):
        return MANUAL, "delegated to hero-skills"
    return PASS, ""


@check("CI-05")
def _(r):
    wfs = workflows(r)
    if not wfs:
        return NA, "no workflows"
    for w in wfs:
        t = w.read_text()
        if w.stem == "auto-approve":
            continue
        # a workflow that runs tests AND triggers on pull_request
        if re.search(r"\bpull_request\b", t) and re.search(r"\b(test|lint|verify|typecheck)\b", t):
            return PASS, w.name
    return FAIL, "no PR test gate"


@check("CI-06")
def _(r):
    wfs = workflows(r)
    if not wfs:
        return NA, "no workflows"
    missing = [w.name for w in wfs if not re.search(r"^permissions:", w.read_text(), re.M)]
    return (FAIL, ",".join(missing)) if missing else (PASS, "")


@check("CI-07")
def _(r):
    wfs = workflows(r)
    if not wfs:
        return NA, "no workflows"
    bad = []
    for w in wfs:
        text = w.read_text()
        if "timeout-minutes" in text:
            continue
        # A workflow whose jobs ONLY call reusable workflows (job-level `uses:`)
        # cannot carry timeout-minutes — GitHub rejects the key on such a job,
        # and the timeout is enforced in the callee. Don't grep-fail the caller.
        try:
            jobs = (yaml.safe_load(text) or {}).get("jobs") or {}
        except Exception:
            jobs = {}
        if jobs and all(isinstance(j, dict) and "uses" in j for j in jobs.values()):
            continue
        bad.append(w.name)
    return (FAIL, f"{len(bad)}/{len(wfs)} workflows lack it") if bad else (PASS, "")


@check("CI-08")
def _(r):
    wfs = workflows(r)
    if not wfs:
        return NA, "no workflows"
    missing = [
        w.name for w in wfs
        if not re.search(r"^concurrency:", w.read_text(), re.M) and w.stem != "auto-approve"
    ]
    return (FAIL, ",".join(missing)) if missing else (PASS, "")


@check("CI-09")
def _(r):
    wfs = workflows(r)
    if not wfs:
        return NA, "no workflows"
    if any(re.search(r"run:\s*just ", w.read_text()) for w in wfs):
        return PASS, ""
    return FAIL, "CI reimplements gates"


@check("GATE-02")
def _(r):
    f = yml(r, ".golangci")
    if not f.is_file():
        return NA, "no config"
    t = uncommented(f.read_text())
    probs = []
    if not re.search(r"^version:\s*[\"']?2", t, re.M):
        probs.append("not v2")
    if re.search(r"shadow:\s*true", t):
        probs.append("no-op shadow")
    if re.search(r"\bgosimple\b", t):
        probs.append("gosimple")
    return (FAIL, ",".join(probs)) if probs else (PASS, "")


@check("GATE-03")
def _(r):
    f = r / ".pre-commit-config.yaml"
    if not f.is_file():
        return NA, "no pre-commit"
    try:
        c = yaml.safe_load(f.read_text())
    except Exception as e:
        return MANUAL, f"unparsable: {e}"
    # Check the HAZARD, not a proxy for it. The condition is "no hook runs
    # at every stage", which `default_stages: [pre-commit]` is the usual way
    # to achieve — but a config where every hook declares its own `stages:`
    # satisfies it too, and greping for the key alone failed that repo for a
    # problem it does not have.
    if c.get("default_stages"):
        return PASS, "default_stages set"
    loose = [h["id"] for r_ in c.get("repos", []) for h in r_.get("hooks", [])
             if h.get("stages") is None]
    if loose:
        return FAIL, f"{len(loose)} hooks run at every stage"
    return PASS, "every hook declares stages"


@check("GATE-06")
def _(r):
    f = r / ".pre-commit-config.yaml"
    if not f.is_file():
        return NA, "no pre-commit"
    t = f.read_text()
    if "conventional-pre-commit" not in t:
        return FAIL, "no conventional-commit hook"
    m = re.search(r"default_install_hook_types:\s*\[([^\]]*)\]", t)
    if m and "commit-msg" not in m.group(1):
        return FAIL, "commit-msg not installed"
    return PASS, ""


@check("CTR-03")
def _(r):
    # Scoped to what SHIPS or DEPLOYS: Dockerfile.prod and the prod compose.
    #
    # Dockerfile.dev is deliberately out of scope. Two repos track
    # minio:latest there and both carry a written reason at the point of
    # difference — the sidecar is recreated on every dev-stack rebuild and
    # the dev image never reaches production. That is documented VARIANCE,
    # and a checker cannot read prose, so the honest move is to scope the
    # check to where the rule is absolute rather than flag a justified
    # exception forever and train people to ignore it.
    #
    # An unpinned image in a PROD compose is a different thing entirely: an
    # upstream change lands unannounced on something holding real data, and
    # Dependabot cannot bump `latest` because there is no version to
    # compare.
    targets = [r / "Dockerfile.prod", yml(r, "docker-compose.prod")]
    hits = []
    for f in targets:
        if not f.is_file():
            continue
        for i, line in enumerate(uncommented(f.read_text()).splitlines(), 1):
            if ":latest" in line:
                hits.append(f"{f.name}:{i}")
    return (FAIL, ", ".join(hits)) if hits else (PASS, "prod pinned")


@check("DOC-01")
def _(r):
    # AGENTS.md first: once DOC-04 lands, CLAUDE.md is a pointer and checking
    # IT for duplicate sections passes vacuously while the real content goes
    # unchecked. Fixing one check must not blind another.
    f = r / "AGENTS.md"
    if not f.is_file():
        f = r / "CLAUDE.md"
    if not f.is_file():
        return NA, "no AGENTS.md or CLAUDE.md"
    heads = [h.strip() for h in re.findall(r"^#{2,3}\s+(.+)$", f.read_text(), re.M)]
    dupes = {h for h in heads if heads.count(h) > 1}
    return (FAIL, "dupe: " + ",".join(sorted(dupes))) if dupes else (PASS, "")


@check("DOC-02")
def _(r):
    if r.name == "hero-template":
        return NA, "generated per clone"
    return (PASS, "") if (r / "HERO.md").is_file() else (FAIL, "missing")


@check("JUST-01")
def _(r):
    f = r / "Justfile"
    if not f.is_file():
        return NA, "no Justfile"
    t = f.read_text()
    # Split by what the recipe presupposes, not by importance. test/lint/
    # typecheck/clean/format describe work any repo has; dev-stack, health and
    # build describe a service you can stand up, probe, and compile. A repo
    # with neither a UI nor a backend has nothing to put in those three, so
    # demanding them buys an empty recipe that exists to satisfy a grep —
    # which is worse than the gap, because the next reader believes it.
    #
    # Same shape as the AUTH-01 / UI-01 / HLT-01 guards: absent subsystem is
    # n/a, not a violation.
    need = ["test", "lint", "typecheck", "clean", "format"]
    if has_ui(r) or has_backend(r) or (r / "Dockerfile.prod").is_file():
        need += ["dev-stack", "health", "build"]
    missing = [n for n in need if not re.search(rf"^{re.escape(n)}\b.*:", t, re.M)]
    return (FAIL, "no " + ",".join(missing)) if missing else (PASS, "")


@check("JUST-03")
def _(r):
    if not has_go(r):
        return NA, "no Go"
    f = r / "Justfile"
    if not f.is_file():
        return NA, "no Justfile"
    t = f.read_text()
    if not re.search(r"^\s*set\s+dotenv-load", t, re.M):
        return PASS, "no global dotenv-load"
    # Present. Whether that is a bug depends on what the repo's Go tests
    # assert, which a grep cannot know — hiro sets it and is currently safe
    # (no lib/config; its config test reads a deliberately suffixed var; .env
    # holds nothing a test reads). Our own rule says a difference with a
    # written reason at the point of difference is VARIANCE, so honour the
    # comment and let a human judge it.
    head = t[: t.find("set dotenv-load")]
    if "dotenv-load" in head or len(head.strip().splitlines()) >= 3:
        return MANUAL, "dotenv-load set, with a rationale — verify it still holds"
    return FAIL, "dotenv-load set with no rationale"


# ── Checkers written to close the MANUAL gap ────────────────────────────
#
# 14 of 43 checks had no checker and reported MANUAL — honest, but it meant a
# third of the register documented drift rather than catching it. These close
# the automatable ones. What stays MANUAL below stays MANUAL for a stated
# reason, not because nobody got to it.


@check("CTR-07")
def _(r):
    f = yml(r, "docker-compose.prod")
    if not f.is_file():
        return NA, "no prod compose"
    try:
        doc = yaml.safe_load(f.read_text())
    except Exception as e:
        return MANUAL, f"unparsable: {e}"
    bad = []
    for name, svc in (doc.get("services") or {}).items():
        if not isinstance(svc, dict):
            continue
        # Two models. Swarm services carry `deploy.restart_policy`; classic
        # compose carries a top-level `restart:`. website and design-system
        # deploy via `docker stack deploy`, so they use the former — checking
        # only `restart:` would report them as violations for using the
        # correct spelling for their platform.
        if "deploy" in svc:
            cond = (svc.get("deploy") or {}).get("restart_policy", {}).get("condition")
            if not cond:
                bad.append(f"{name}: no deploy.restart_policy")
            continue
        pol = svc.get("restart", None)
        # `restart: no` is YAML false, and is CORRECT for a one-shot setup job
        # — it must not be restarted. Treat an explicit false as a policy.
        if pol is None:
            # Setup/init jobs that simply omit it are still wrong: compose
            # defaults to `no`, but the intent should be written down.
            bad.append(f"{name}: no restart policy")
    return (FAIL, "; ".join(bad)) if bad else (PASS, "all services declare one")


@check("CTR-05")
def _(r):
    f = r / "supervisor.mjs"
    if not f.is_file():
        return NA, "no supervisor"
    s = f.read_text()
    probs = []
    # The bug: keeping the code in a local and only applying it from an
    # unref'd timer. When the peer child exits promptly the event loop drains
    # first and Node exits 0 — a crash reported as a graceful stop, so
    # `restart: on-failure` never fires and the unit stays dead.
    if "process.exitCode" not in s:
        probs.append("does not set process.exitCode")
    if re.search(r"setTimeout\(\s*\(\)\s*=>\s*process\.exit\(\s*exitCode\s*\)", s):
        probs.append("exits from an unref'd timer with a local code")
    # A child killed by our own SIGTERM reports code===null. Treating that as
    # a failure makes every graceful stop exit non-zero.
    if "code === null" not in s and "code===null" not in s:
        probs.append("does not treat code===null during teardown as clean")
    return (FAIL, "; ".join(probs)) if probs else (PASS, "exit contract intact")


@check("CTR-06")
def _(r):
    f = r / "dev.sh"
    if not f.is_file():
        return NA, "no dev.sh"
    s = uncommented(f.read_text())
    if not re.search(r"shutdown\(\)\s*\{", s):
        return MANUAL, "no shutdown() to judge"
    probs = []
    # shutdown must take a code and propagate it; the old shape hardcoded
    # `exit 0`, making a segfaulting mongod indistinguishable from
    # `docker compose down`.
    if not re.search(r'code="?\$\{1:-0\}"?', s):
        probs.append("shutdown() takes no exit code")
    if re.search(r"^\s*exit 0\s*$", s, re.M) and 'exit "$code"' not in s:
        probs.append("hardcodes exit 0")
    # The watchdog (a child died unexpectedly) must pass non-zero.
    if "shutdown 1" not in s:
        probs.append("watchdog does not pass a failing code")
    return (FAIL, "; ".join(probs)) if probs else (PASS, "propagates the code")


def _node_majors(r):
    """Every Node major this repo pins, and where."""
    out = {}
    n = r / ".nvmrc"
    if n.is_file():
        m = re.search(r"\d+", n.read_text())
        if m:
            out[".nvmrc"] = m.group(0)
    for df in sorted(r.glob("Dockerfile*")):
        for m in re.finditer(r"FROM node:(\d+)", df.read_text()):
            out[f"{df.name}:node"] = m.group(1)
        for m in re.finditer(r"distroless/nodejs(\d+)", df.read_text()):
            out[f"{df.name}:runtime"] = m.group(1)
    for w in workflows(r):
        for m in re.finditer(r"node-version:\s*'?(\d+)'?", w.read_text()):
            out[f"{w.name}"] = m.group(1)
    return out


@check("CTR-01")
def _(r):
    pins = _node_majors(r)
    if not pins:
        return NA, "no node pins"
    vals = set(pins.values())
    if len(vals) > 1:
        detail = ", ".join(f"{k}={v}" for k, v in sorted(pins.items()))
        return FAIL, f"majors disagree: {detail}"
    # Agreement is necessary but not sufficient: CI must ASSERT it, or the
    # next edit silently re-splits build-on-N / run-on-M.
    asserts = any("node majors agree" in w.read_text() for w in workflows(r))
    if not asserts:
        return FAIL, f"all on {vals.pop()}, but CI does not assert it"
    return PASS, f"node {vals.pop()}, asserted in CI"


@check("CTR-02")
def _(r):
    if not has_go(r):
        return NA, "no Go"
    out = {}
    for gm in sorted(r.glob("*/go.mod")):
        m = re.search(r"^go (\d+\.\d+)", gm.read_text(), re.M)
        if m:
            out[f"{gm.parent.name}/go.mod"] = m.group(1)
    for df in sorted(r.glob("Dockerfile*")):
        for m in re.finditer(r"FROM golang:(\d+\.\d+)", df.read_text()):
            out[df.name] = m.group(1)
    for w in workflows(r):
        for m in re.finditer(r"go-version:\s*'?(\d+\.\d+)'?", w.read_text()):
            out[w.name] = m.group(1)
    if not out:
        return NA, "no go pins"
    vals = set(out.values())
    if len(vals) > 1:
        return FAIL, "versions disagree: " + ", ".join(f"{k}={v}" for k, v in sorted(out.items()))
    return PASS, f"go {vals.pop()} everywhere"


# config file -> the token that proves something RUNS it.
_RUNNERS = {
    ".golangci.y*ml": "golangci-lint",
    ".markdownlint.yaml": "markdownlint",
    ".prettierrc": "prettier",
    "eslint.config.js": "eslint",
    ".secrets.baseline": "detect-secrets",
}


@check("GATE-01")
def _(r):
    """Trace every committed tool config to something that executes it.

    Dead config is worse than none: it reads as a gate. auth carried a
    .golangci.yaml for years that no hook and no workflow invoked.
    """
    haystack = ""
    for p in (r / ".pre-commit-config.yaml", r / "Justfile"):
        if p.is_file():
            haystack += p.read_text()
    for w in workflows(r):
        haystack += w.read_text()
    for sub in ("ui", "src"):
        pj = r / sub / "package.json"
        if pj.is_file():
            haystack += pj.read_text()
    pj = r / "package.json"
    if pj.is_file():
        haystack += pj.read_text()

    dead = []
    for cfg, token in _RUNNERS.items():
        found = list(r.glob(cfg)) + list(r.glob(f"ui/{cfg}"))
        if not found:
            continue
        if token not in haystack:
            dead.append(f"{cfg} (nothing runs {token})")
    return (FAIL, "; ".join(dead)) if dead else (PASS, "every config has a runner")


@check("JUST-02")
def _(r):
    """A shebang-less recipe must not rely on a pipeline's exit status.

    The original finding here — "no shebang means no early exit, so a failing
    step reports success" — is FALSE, and was verified false: `just` runs each
    line in its own shell and ABORTS the recipe on the first non-zero line
    ("error: Recipe `x` failed on line N"). Multi-line alone is not a hazard.

    The real hazard is narrower. A pipeline's exit status is its LAST
    command's, and there is no `pipefail` without a `#!/usr/bin/env bash`
    recipe — so `false | cat` succeeds and the recipe carries on. That is the
    silent success, and it needs a pipe, not merely a second line.

    hero-template's `health` recipe documents exactly this trap: it avoids
    `curl -fsS ... | jq` because the pipe would swallow curl's status and make
    the documented "non-zero on 503" a lie.
    """
    f = r / "Justfile"
    if not f.is_file():
        return NA, "no Justfile"
    lines = f.read_text().split("\n")
    bad, i = [], 0
    while i < len(lines):
        m = re.match(r"^([a-z][a-z0-9-]*)(\s+\S+)*:", lines[i])
        if not m:
            i += 1
            continue
        name, body, j = m.group(1), [], i + 1
        while j < len(lines) and (lines[j].startswith((" ", "\t")) or not lines[j].strip()):
            if lines[j].strip():
                body.append(lines[j])
            j += 1
        # A shebang recipe runs as one script and can set -o pipefail itself.
        if body and body[0].strip().startswith("#!"):
            i = j
            continue
        for b in body:
            if b.strip().startswith("#"):
                continue
            # A real pipe, not `||`.
            if re.search(r"[^|]\|[^|]", b):
                bad.append(f"{name}: {b.strip()[:40]}")
        i = j
    if bad:
        return FAIL, "unguarded pipe: " + "; ".join(bad)
    return PASS, "no unguarded pipes"


# Files allowed to sit at the repo root. Everything else belongs under docs/.
_ROOT_OK = re.compile(
    r"^("
    # Entry docs and the compliance register. These BELONG at the root — an
    # earlier version of this pattern anchored on the stem only, so README.md
    # never matched ^README$ and the check flagged every file it exists to
    # permit.
    r"(README|CLAUDE|AGENTS|HERO|DESIGN|CONTROLS|CHECKS|CONSISTENCY|CONTRIBUTING|SECURITY|CHANGELOG|LICENSE)"
    r"(\.(md|yaml|yml|txt))?"
    # Harness + build files.
    r"|Justfile|Dockerfile.*|docker-compose.*|go\.work.*|dev\.sh|supervisor\.mjs"
    r"|package(-lock)?\.json|tsconfig.*\.json|components\.json|registry\.json"
    r"|vite\.config\.ts|playwright\.config\.ts|eslint.*\.(js|mjs|ts)|firebase\.json"
    r"|uv\.lock|pyproject\.toml|terraform\.auto\.tfvars\.example|.*\.code-workspace"
    r")$"
)


@check("PLACE-04")
def _(r):
    _rc, out = sh(r, "git ls-files --full-name -- ':(exclude)*/*'")
    loose = []
    for f in out.splitlines():
        f = f.strip()
        if not f or f.startswith("."):
            continue
        if _ROOT_OK.match(f):
            continue
        loose.append(f)
    return (FAIL, ", ".join(sorted(loose))) if loose else (PASS, "root is clean")


@check("DOC-03")
def _(r):
    if not (r / "docs").is_dir():
        return NA, "no docs/"
    stray = (r / "docs" / "design").is_dir()
    return (FAIL, "docs/design/ — use docs/superpowers/specs/") if stray else (PASS, "")


@check("HLT-03")
def _(r):
    if not has_go(r):
        return NA, "no Go backend"
    _rc, out = sh(r, "git grep -lI -E 'IsDev|Environment' -- 'lib/**/*.go' 2>/dev/null")
    if not out:
        return NA, "no environment gate found"
    # The failure mode is comparing the string instead of asking the type:
    # `!= \"production\"` opens disclosure in staging.
    _rc, bad = sh(
        r,
        "git grep -nI -E '(Environment|env)\\s*!=\\s*\"production\"' -- '*.go' 2>/dev/null",
    )
    if bad:
        return FAIL, "string compare against \"production\": " + bad.splitlines()[0][:60]
    return MANUAL, "no string-compare found; confirm probe errors are gated on IsDev()"


@check("DOC-04")
def _(r):
    a, c = r / "AGENTS.md", r / "CLAUDE.md"
    if not a.is_file():
        return FAIL, "no AGENTS.md (the cross-vendor standard)"
    if not c.exists() and not c.is_symlink():
        return PASS, "AGENTS.md only"
    # A SYMLINK, not a prose pointer and certainly not a copy. A pointer file
    # is still a second file: it can accumulate content and drift. A symlink
    # cannot — there is exactly one set of bytes, and git stores it as mode
    # 120000 rather than a blob.
    if not c.is_symlink():
        return FAIL, "CLAUDE.md is a real file — it must be a symlink to AGENTS.md"
    target = os.readlink(c)
    if pathlib.PurePath(target).name != "AGENTS.md":
        return FAIL, f"CLAUDE.md symlinks to {target}, not AGENTS.md"
    return PASS, "CLAUDE.md -> AGENTS.md (symlink)"


@check("JUST-04")
def _(r):
    f = r / "Justfile"
    if not f.is_file():
        return NA, "no Justfile"
    bad = []
    _rc, out = sh(r, "just --summary 2>/dev/null")
    if out:
        bad += ["Justfile:" + x for x in out.split()
                if x in ("dev", "dev-ui", "dev-service", "dev-mongo", "dev-redis", "preview")]
    # SUB-files count. A root Justfile with no host recipe proves nothing if
    # ui/Justfile still has `dev` and service/Makefile still has `run` — the
    # rule is that no path starts a server on the host, not that one file
    # doesn't. The root-only version of this check passed all five repos while
    # four of them shipped exactly that.
    # A language virtual environment is the same evasion as a host recipe: it
    # is an environment that is not the container. None exist in the fleet
    # today; the check is here so one cannot arrive quietly.
    for venv in ("venv", ".venv", "virtualenv"):
        if (r / venv).is_dir():
            bad.append(f"{venv}/ — the container is the environment")
    for sub in list(r.glob("*/Justfile")) + list(r.glob("*/Makefile")):
        if "node_modules" in str(sub):
            continue
        for i, line in enumerate(sub.read_text().splitlines(), 1):
            m = re.match(r"^(run|dev|serve|start):", line)
            if m:
                bad.append(f"{sub.parent.name}/{sub.name}:{i} {m.group(1)}")
    if bad:
        return FAIL, "host-run: " + ", ".join(bad)
    return PASS, "containerized only"


# The one spelling the family converged on, once AUTH-02 settled on the BFF:
# unprefixed, and never VITE_ — that prefix inlines a value into the client
# bundle, which is the opposite of what server-side config means.
_AUTH_VARS = re.compile(r"^[A-Z_]*(AUTH|OAUTH)[A-Z_]*(ISSUER|CLIENT_ID)[A-Z_]*$")


@check("AUTH-01")
def _(r):
    # auth IS the IdP — it has no OAuth client to configure, so "consumer
    # reads the same client vars" cannot apply to it. The rule's own carve-out.
    if r.name == "auth":
        return NA, "is the IdP, not a consumer"
    if not has_ui(r):
        return NA, "no UI to log in from"
    names = set()
    for f in list(r.glob(".env*.example")):
        for line in f.read_text().splitlines():
            k = line.split("=", 1)[0].strip()
            if _AUTH_VARS.match(k):
                names.add(k)
    if not names:
        return FAIL, "no OAuth env vars — auth not integrated"
    # Compare against every sibling IN THE FAMILY: the point is one scheme
    # fleet-wide, so a repo cannot be judged alone — but "fleet" means the five
    # repos this register governs, not every checkout that happens to sit in
    # this directory. See FAMILY.
    others = {}
    for name in FAMILY:
        d = repo_path(name)
        if not (d / ".git").exists() or d == r:
            continue
        for f in d.glob(".env*.example"):
            for line in f.read_text().splitlines():
                k = line.split("=", 1)[0].strip()
                if _AUTH_VARS.match(k):
                    others.setdefault(k, d.name)
    foreign = {k: v for k, v in others.items() if k not in names}
    if foreign:
        return FAIL, "own: " + ",".join(sorted(names)) + " | elsewhere: " + ",".join(sorted(foreign))
    return PASS, ",".join(sorted(names))


# Where a repo's BFF lives. Two spellings because two layouts: STRUCT-08's
# ui/ + lib/ + service/ split, and design-system, which is a single Node app
# with src/ at the root and no backend to front.
_BFF_PATHS = ("ui/src/lib/server/auth.ts", "src/lib/server/auth.ts")

# Anchored at column 0, which is what keeps this off prose ABOUT an export:
# a `//`-commented or block-quoted mention is indented or prefixed, so it
# cannot match. The same trap uncommented() exists for on the YAML side.
_TS_EXPORT = re.compile(
    r"^export\s+(?:async\s+)?(?:function|const|class|type|interface)\s+([A-Za-z0-9_$]+)",
    re.M,
)


def bff_exports(repo):
    """The exported surface of a repo's hand-rolled BFF, or None if it has no
    BFF. Returns a set of exported names."""
    for rel in _BFF_PATHS:
        f = repo / rel
        if f.is_file():
            return set(_TS_EXPORT.findall(f.read_text()))
    return None


def bff_source(repo):
    """The BFF's server auth.ts text, or None. AUTH-05/06 pin BEHAVIOUR, so they
    read the source, not just the export names — the same reason AUTH-04 reads
    the test file: refreshTokens has the same name in every copy and differs
    only in what it does with a 5xx."""
    for rel in _BFF_PATHS:
        f = repo / rel
        if f.is_file():
            return f.read_text()
    return None


def bff_test(repo):
    """The test file next to the BFF, or None."""
    for rel in _BFF_PATHS:
        cand = repo / rel.replace(".ts", ".test.ts")
        if cand.is_file():
            return cand
    return None


def login_route(repo):
    """The OAuth login route text, or "". The filename varies across the fleet
    (routes/auth/login.ts vs routes/auth.login.ts), so match any non-test
    *login*.ts under a routes dir."""
    for base in ("ui/src/routes", "src/routes"):
        d = repo / base
        if not d.is_dir():
            continue
        for f in sorted(d.rglob("*login*.ts")):
            if not f.name.endswith(".test.ts"):
                return f.read_text()
    return ""


@check("AUTH-03")
def _(r):
    # auth is carved out for the same reason AUTH-01 carves it out: it is the
    # IdP. Its ui/src/lib/server/auth.ts is a console BFF pointed at ITSELF,
    # with a multi-surface client model (Surface, clientIdForSurface,
    # callbackPathForSurface) that no consumer has or should have. Comparing it
    # to the consumers reports variance as drift, forever — and a check that
    # cannot go green is one people learn to ignore.
    #
    # It is NOT carved out because its copy is safe. auth hand-rolls
    # pkceChallenge, sanitizeReturnTo and exchangeCode too, so a fix to any of
    # them has to be hand-carried there as well; this check just cannot be the
    # thing that tells you. See AUTH-03's `why`.
    if r.name == "auth":
        return NA, "is the IdP — its console BFF is a different shape by design"
    mine = bff_exports(r)
    if mine is None:
        return NA, "no BFF"
    others = {}
    for name in FAMILY:
        d = repo_path(name)
        if d == r or name == "auth" or not (d / ".git").exists():
            continue
        got = bff_exports(d)
        if got is not None:
            others[name] = got
    # Nothing to compare against is not a pass. A lone copy cannot be shown to
    # agree with anything, and reporting PASS here would mean the check goes
    # green precisely when it has done no work — the failure it exists to catch,
    # wearing its own uniform.
    if not others:
        return MANUAL, f"{len(mine)} exports; no other BFF in the family to compare against"
    # Outlier detection, not pairwise diffing: an export is only this repo's
    # problem if NO other copy has it (it gained one) or EVERY other copy has it
    # (it lost one). Where two copies agree and a third differs, only the third
    # is reported — otherwise one divergence would paint every repo red and
    # nobody could tell which one moved.
    # REPORTS, NEVER FAILS. This check was written to catch "a bug fixed in one
    # copy silently persists in the others", and it cannot: sanitizeReturnTo has
    # the same NAME in all four copies and was exploitable in two of them, so a
    # surface comparison saw agreement over a live open redirect. AUTH-04 owns
    # that job now, by pinning behaviour instead of names.
    #
    # What is left here is real but weaker: the copies' shapes differ, and it is
    # worth a periodic look. It must not FAIL, because a name cannot distinguish
    # the two reasons a surface is smaller — "does not need it" from "missing a
    # fix" — and both are present in this fleet. website and design-system have
    # no post-login bearer, so they legitimately have no refresh machinery;
    # design-system is a separate lineage that decomposes the same job under
    # different names. Failing them taught nobody anything and trained everyone
    # to skip the report, which is how a register dies.
    #
    # MANUAL, on PLACE-01's precedent: a documented difference should not go
    # green unexamined, but nor should it sit red forever.
    union = set().union(*others.values())
    common = set.intersection(*others.values())
    gained = mine - union
    lost = common - mine
    if not gained and not lost:
        # "no outlier exports vs", not "agrees with": this repo is not the one
        # whose shape moved. It says nothing about whether the code behind those
        # names agrees — AUTH-04 is what speaks to that.
        return PASS, f"{len(mine)} exports, no outlier vs " + ",".join(sorted(others))
    detail = []
    if gained:
        detail.append("only here: " + ",".join(sorted(gained)))
    if lost:
        detail.append("missing: " + ",".join(sorted(lost)))
    return MANUAL, " | ".join(detail) + " — re-verify these are needs, not drift"


# The two tells of a browser-side implementation. Either one alone is
# disqualifying, and they fail differently:
#
#   VITE_ on an OAuth var — Vite inlines it into the client bundle at build
#   time. The value is "server-side config" in name only; it ships to every
#   visitor.
#
#   a token in localStorage/sessionStorage — any script on the page can read
#   it. That is the whole difference between an XSS that defaces a page and
#   one that walks off with a live credential.
#
# NO \b IN THESE PATTERNS. git grep's engine does not support the GNU \b
# escape: it matches nothing, silently, with no error and exit 1 — which a
# checker reads as "clean". `\bVITE_` passed every repo in the fleet including
# the one whose config is inlined into its bundle today. It is the same trap as
# `govet: {shadow: true}` and it is why these patterns get probe-tested against
# a planted violation rather than eyeballed.
_BROWSER_OAUTH = (
    r"VITE_[A-Z_]*(AUTH|OAUTH)",
    r"(localStorage|sessionStorage)\.setItem\([^)]*(token|session)",
)


@check("AUTH-02")
def _(r):
    # auth ISSUES the tokens rather than consuming them, so "which client
    # model does it use" has no answer for it. Same carve-out as AUTH-01.
    if r.name == "auth":
        return NA, "is the IdP, not a consumer"
    if not has_ui(r):
        return NA, "no UI to log in from"

    # git grep, not grep -r: a recursive grep reads gitignored build output and
    # node_modules, which has already produced false findings in this register.
    #
    # The exclusions are all one idea: prose ABOUT the banned model is not the
    # banned model — the uncommented() lesson wearing a third hat. Docs explain
    # the ban, and the register must SPELL the forbidden names in order to ban
    # them: CHECKS.yaml quotes them in `why`, and this very file carries them as
    # regex literals. Without this, hero-template fails the rule it is the
    # reference for, and the failing "evidence" is the rule's own text.
    scope = "-- . ':(exclude)*.md' " + " ".join(
        f"':(exclude){p}'" for p in REGISTER_FILES
    )
    hits = []
    for pat in _BROWSER_OAUTH:
        _, out = sh(r, f"git grep -lEi {shlex.quote(pat)} {scope}")
        hits += [f for f in out.splitlines() if f]

    # Match the BFF by suffix, never by a fixed path: design-system has no ui/
    # subdirectory (it IS the UI), so its BFF sits at src/lib/server/auth.ts.
    # Hardcoding ui/ would fail the repo the fleet took these names FROM.
    _, tracked = sh(r, "git ls-files")
    bff = [f for f in tracked.splitlines() if f.endswith("lib/server/auth.ts")]

    if hits:
        return FAIL, "OAuth runs in the browser: " + ", ".join(sorted(set(hits))[:3])
    if not bff:
        return FAIL, "no BFF (lib/server/auth.ts) — auth not integrated"
    return PASS, f"BFF at {bff[0]}, no client-side OAuth"


@check("PLACE-05")
def _(r):
    if not list(r.glob("Dockerfile*")):
        return NA, "no Dockerfile"
    if (r / "Dockerfile").is_file():
        return FAIL, "bare Dockerfile — which environment does it build?"
    missing = [n for n in ("Dockerfile.dev", "Dockerfile.prod") if not (r / n).is_file()]
    return (FAIL, "missing " + ", ".join(missing)) if missing else (PASS, "dev + prod")


@check("STRUCT-08")
def _(r):
    if not has_go(r):
        return NA, "no Go backend"
    missing = [d for d in ("ui", "lib", "service") if not (r / d).is_dir()]
    return (FAIL, "missing " + ", ".join(missing)) if missing else (PASS, "ui + lib + service")


def fenced_trees(repo):
    """Directories the repo has already declared are not its source, read from
    .prettierignore.

    Not a hardcoded folder list: the repo states this itself, and PLACE-06 has
    no business inventing its own answer. design-system fences mockup/ out of
    prettier, eslint, tsconfig and docker alike — reading the fence keeps this
    check honest for any repo that vendors something later.
    """
    f = repo / ".prettierignore"
    if not f.is_file():
        return []
    out = []
    for line in uncommented(f.read_text()).splitlines():
        s = line.strip().rstrip("/")
        # Only plain directory prefixes. A glob (dist/**, *.min.js) is about
        # build output, not a vendored tree, and guessing at glob semantics here
        # would quietly widen the carve-out.
        if s and not s.startswith("!") and not any(c in s for c in "*?[]"):
            out.append(s)
    return out


@check("PLACE-06")
def _(r):
    _rc, out = sh(r, "git ls-files '*.yml' | grep -v node_modules")
    files = [x for x in out.splitlines() if x]
    if not files:
        return PASS, "all .yaml"
    fences = fenced_trees(r)
    stray = [x for x in files if not any(x.startswith(d + "/") for d in fences)]
    if stray:
        return FAIL, f"{len(stray)} .yml files (use .yaml): " + " ".join(stray[:3])
    # Name only the fences that actually cover a .yml. .prettierignore also
    # lists lockfiles and generated files, and reporting those as "trees" would
    # make the exception look broader than it is.
    covering = sorted({d for d in fences for x in files if x.startswith(d + "/")})
    # MANUAL, not PASS — same reasoning as PLACE-01: a documented exception
    # should not go green unexamined, but nor should it stay red forever and
    # train people to ignore the report.
    return MANUAL, f"{len(files)} .yml only under fenced {','.join(covering)}/ — re-verify it is still vendored"


@check("CTR-08")
def _(r):
    f = yml(r, "docker-compose.dev")
    if not f.is_file():
        return NA, "no dev compose"
    try:
        doc = yaml.safe_load(f.read_text())
    except Exception as e:
        return MANUAL, f"unparsable: {e}"
    mounts = []
    for svc in (doc.get("services") or {}).values():
        if not isinstance(svc, dict):
            continue
        for v in (svc.get("volumes") or []):
            if isinstance(v, str) and (v.startswith("./") or v.startswith(".:")):
                mounts.append(v.split(":")[0])
    if not mounts:
        return FAIL, "no source mount — a change needs a rebuild"
    # `.:/app` mounts the WHOLE repo, which covers the UI and everything else —
    # a superset of ./ui, not a gap. An earlier version of this check looked
    # only for ./ui or ./src and failed the two repos that do it MORE
    # thoroughly. website documents why it needs the wider mount: vite's envDir
    # is the repo root, not ui/, so a narrower mount would miss the .env the
    # config reads.
    if "." in mounts:
        return PASS, "whole repo (.:/app)"
    if not [m for m in mounts if m in ("./ui", "./src")]:
        return FAIL, "backend mounted but not the UI: " + ", ".join(sorted(set(mounts)))
    return PASS, ", ".join(sorted(set(mounts)))


@check("DATA-01")
def _(r):
    if not has_go(r):
        return NA, "no Go backend"
    _rc, uses_mongo = sh(r, "git grep -lI 'mongo' -- '*/go.mod' 2>/dev/null")
    if not uses_mongo:
        return NA, "no MongoDB"
    _rc, out = sh(r, "git grep -nI 'Migrate(' -- 'service/main.go' 2>/dev/null")
    if not out:
        return FAIL, "no migration runs at boot"
    return PASS, out.splitlines()[0].split(":")[0] + " calls Migrate at boot"


@check("UI-01")
def _(r):
    if not has_ui(r):
        return NA, "no UI"
    _rc, out = sh(r, "git ls-files | grep -E 'version-gate|use-version-check'")
    if not out:
        return FAIL, "no version check — a stale tab keeps calling a moved API"
    # The files existing is not the point — the gate RENDERING is. A VersionGate
    # imported but never mounted has already shipped once in this family, doing
    # nothing, while this check reported PASS on the strength of the file being
    # there. It was caught by tsc's noUnusedLocals, which is luck, not a gate.
    #
    # So look for the JSX, in a file that is not the component or its own test.
    # An import alone proves nothing: it is exactly what the broken version had.
    _rc, used = sh(
        r,
        "git grep -l '<VersionGate' -- '*.tsx' "
        "':(exclude)*version-gate*' ':(exclude)*.test.tsx' ':(exclude)*.spec.tsx'",
    )
    if not used:
        return FAIL, "version-gate exists but nothing renders it — a gate that cannot fire"
    return PASS, f"{len(out.splitlines())} files, mounted in {used.splitlines()[0]}"


# Inputs that must never survive sanitizeReturnTo, and the reason each exists.
# This is a CORPUS, not a style rule: every entry is a real bypass someone has
# actually shipped, and it only grows.
#
# The backslash entry is why this check exists at all. "/\evil.com" was live in
# hero-template and hiro: the guard tested startsWith("//"), which it does not
# match, and browsers normalize "\" to "/" there — so it resolved to
# https://evil.com/ out of a Location header on the LOGIN SUCCESS path.
# design-system had the correct check the whole time. Three hand-rolled copies,
# one right, and nothing said a word for months.
#
# AUTH-03 could never have caught it: sanitizeReturnTo has the same NAME in all
# four copies, so a surface comparison sees agreement. Only the behaviour
# differed. When the next bypass turns up, add it here and every copy that does
# not defend against it goes red at once — which is the whole point, because the
# failure mode is fixing it in the copy you happened to be looking at.
_RETURNTO_ATTACKS = (
    (r"//evil", "protocol-relative"),
    (r"\\evil", "backslash the browser normalizes to protocol-relative"),
    (r"https://evil", "absolute URL"),
    (r"javascript:", "scheme"),
)


# A name that IS a credential. Anything matching this belongs in `secrets`.
#
# The DSN carve-out is not a fudge: a Sentry DSN is a public write-only ingest
# key that Vite inlines into the bundle every visitor downloads. Calling it a
# credential because it contains no keyword, or hiding it in `secrets`, would be
# cargo-culting the shape of the rule instead of its reason.
_CREDENTIAL = re.compile(r"[A-Z_]*(TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Z_]*$|[A-Z_]+_KEY$")


def _ci_refs(repo):
    """Every ${{ secrets.X }} / ${{ vars.X }} in a repo's workflows, as
    {name: {namespace, ...}}. Reads the workflows as text on purpose: a value
    can appear anywhere (env:, with:, run:), and only the reference matters."""
    out = {}
    for wf in workflows(repo):
        for ns, name in re.findall(
            r"\$\{\{\s*(secrets|vars)\.([A-Z_][A-Z0-9_]*)\s*\}\}", wf.read_text()
        ):
            out.setdefault(name, set()).add(ns)
    return out


@check("PRE-01")
def _(r):
    if not precommit(r):
        return FAIL, "no .pre-commit-config.yaml — nothing runs before a commit"
    missing = _missing_hooks(r, {
        "detect-secrets": ["detect-secrets"],
        "detect-private-key": ["detect-private-key"],
        "no-commit-to-branch": ["no-commit-to-branch"],
        "semgrep": ["semgrep"],
    })
    return (FAIL, "missing security hooks: " + ",".join(missing)) if missing \
        else (PASS, "secret/private-key/branch/SAST hooks present")


@check("PRE-02")
def _(r):
    if not precommit(r):
        return FAIL, "no .pre-commit-config.yaml"
    missing = _missing_hooks(r, {
        "end-of-file-fixer": ["end-of-file-fixer"],
        "trailing-whitespace": ["trailing-whitespace"],
        "check-yaml": ["check-yaml"],
        "check-merge-conflict": ["check-merge-conflict"],
        "check-added-large-files": ["check-added-large-files"],
        "conventional-commit": ["conventional-pre-commit", "conventional-commit"],
    })
    return (FAIL, "missing hygiene hooks: " + ",".join(missing)) if missing \
        else (PASS, "file-hygiene hooks present")


@check("PRE-03")
def _(r):
    if not has_go(r):
        return NA, "no Go"
    if not precommit(r):
        return FAIL, "no .pre-commit-config.yaml"
    missing = _missing_hooks(r, {
        "go-fmt": ["go-fmt", "gofmt", "gofumpt"],
        "go-vet": ["go-vet"],
        "go-mod-tidy": ["go-mod-tidy", "mod-tidy"],
        "golangci-lint": ["golangci"],
    })
    return (FAIL, "missing Go hooks: " + ",".join(missing)) if missing \
        else (PASS, "go fmt/vet/mod-tidy/golangci-lint all hooked")


@check("PRE-04")
def _(r):
    if not has_node(r):
        return NA, "no front-end"
    if not precommit(r):
        return FAIL, "no .pre-commit-config.yaml"
    missing = _missing_hooks(r, {
        "eslint": ["eslint"],
        "typecheck": ["tsc", "typecheck"],
    })
    return (FAIL, "missing Node hooks: " + ",".join(missing)) if missing \
        else (PASS, "eslint + typecheck hooked")


@check("PRE-05")
def _(r):
    if not has_python(r):
        return NA, "no Python in this repo"
    if not precommit(r):
        return FAIL, "no .pre-commit-config.yaml"
    missing = _missing_hooks(r, {
        "ruff": ["ruff"],
        "type-checker": ["mypy", "pyright"],
    })
    return (FAIL, "missing Python hooks: " + ",".join(missing)) if missing \
        else (PASS, "ruff + type checker hooked")


@check("CI-11")
def _(r):
    refs = _ci_refs(r)
    if not refs:
        return NA, "no workflow config references"
    bad = sorted(n for n, ns in refs.items() if "vars" in ns and _CREDENTIAL.match(n))
    if bad:
        return FAIL, "credential in vars (unmasked, world-readable): " + ",".join(bad)
    creds = sorted(n for n in refs if _CREDENTIAL.match(n))
    return PASS, f"{len(creds)} credentials, all in secrets"


@check("CI-12")
def _(r):
    mine = _ci_refs(r)
    if not mine:
        return NA, "no workflow config references"
    # Cross-repo by necessity: a split is invisible from inside one repo, which
    # is exactly why it survives. Compare against the FAMILY, not every checkout
    # beside us — see FAMILY.
    fleet = {}
    for name in FAMILY:
        d = repo_path(name)
        if not (d / ".git").exists():
            continue
        for k, v in _ci_refs(d).items():
            fleet.setdefault(k, {}).setdefault(name, set()).update(v)
    split = []
    for name, per_repo in fleet.items():
        if name not in mine:
            continue
        namespaces = set().union(*per_repo.values())
        if len(namespaces) > 1:
            others = sorted(
                f"{rp}:{'/'.join(sorted(ns))}" for rp, ns in per_repo.items()
            )
            split.append(f"{name} ({', '.join(others)})")
    if split:
        return FAIL, "read from both namespaces: " + "; ".join(sorted(split))
    return PASS, f"{len(mine)} names, each one namespace fleet-wide"


@check("AUTH-04")
def _(r):
    if r.name == "auth":
        return NA, "is the IdP, not a consumer"
    if bff_exports(r) is None:
        return NA, "no BFF"
    # The test file next to the BFF. Read the TEST, not the implementation:
    # four copies implement this four ways (design-system is a separate lineage
    # entirely), so comparing code is noise. What must agree is the behaviour.
    tf = None
    for rel in _BFF_PATHS:
        cand = r / rel.replace(".ts", ".test.ts")
        if cand.is_file():
            tf = cand
            break
    if tf is None:
        return FAIL, "BFF has no test file — nothing pins the open-redirect guard"
    src = tf.read_text()
    if "sanitizeReturnTo" not in src:
        return FAIL, f"{tf.name} never exercises sanitizeReturnTo"
    missing = [why for pat, why in _RETURNTO_ATTACKS if not re.search(re.escape(pat), src)]
    if missing:
        return FAIL, "open-redirect corpus not asserted: " + "; ".join(missing)
    # PASS means the vectors are EXERCISED, not that they pass — the repo's own
    # CI proves that, and it runs these tests on every PR. Same division of
    # labour as UI-01: this register checks the gate exists and is wired; the
    # repo's suite proves it works.
    return PASS, f"{len(_RETURNTO_ATTACKS)} attack vectors asserted in {tf.name}"


# ── VNDR-01: the design-token hook's behaviour, pinned by an external corpus ──
#
# Why the corpus lives HERE rather than being read from each repo's own
# vendored test file: see CHECKS.yaml's VNDR-01 `why:` (an early draft did the
# latter and passed hero-template/hiro for the wrong reason — the AUTH-03
# blindness one level down, since a corpus vendored in the same PR as its hook
# necessarily agrees with it).
#
# So the corpus lives HERE, external to every consumer, and each repo's
# COMMITTED hook is executed against it directly. Two cases below
# (comment_hex, prose_hex) exist because hero-template's copy, as of this
# check's authoring (2026-07-20), had not yet absorbed a refinement (strip
# comments; require a quote prefix, since a colour in JSX is always a string
# and prose is not) that originated in a different consumer's independently-
# reconstituted copy. Their presence here is what turns "back-port it" from a
# judgement call into a green checkmark — and, going forward, into a red one
# the moment any repo's copy regresses on either case, not just hero-template's.
#
# case NAME expect(hit|miss|exit:N) SUBSTRING_OR_NONE CONTENT EXT
_VENDOR_CORPUS = (
    ("shadow_first", "hit", "Shadow", '<div className="shadow-md rounded" />', "tsx"),
    ("shadow_none", "miss", "Shadow", '<div className="shadow-none rounded" />', "tsx"),
    ("shadow_cn", "hit", "Shadow", '<div className={cn("shadow-lg", x)} />', "tsx"),
    ("cn_margin", "hit", "Margin", '<div className={cn("mb-4", x)} />', "tsx"),
    ("arb_bracket", "hit", "Arbitrary", '<div className="w-[300px]" />', "tsx"),
    ("fp_data_variant", "miss", "Arbitrary", '<div className="data-[state=open]:bg-muted" />', "tsx"),
    ("fp_maxw", "miss", "Margin", '<div className="max-w-md" />', "tsx"),
    ("zindex", "hit", "z-index", '<div className="z-50" />', "tsx"),
    ("dark_override", "hit", "dark:", '<div className="dark:bg-muted" />', "tsx"),
    ("palette", "hit", "Raw palette", '<div className="bg-zinc-100" />', "tsx"),
    ("component_hex", "hit", "Color literal", '<div style={{color:"#3D4AB8"}} />', "tsx"),
    ("href_hex", "miss", "Color literal", '<a href="#faq">FAQ</a>', "tsx"),
    ("css_theme_hex", "miss", "Color literal", "@theme{--color-x:#ff0000;}", "css"),
    ("css_plain_hex", "hit", "Color literal", "a{color:#ff0000}", "css"),
    ("clean_file", "miss", "  - ", '<div className="bg-background gap-4" />', "tsx"),
    # hero-template's copy lacked this refinement as of this check's authoring
    # (2026-07-20) — see the block comment above.
    ("prose_hex", "miss", "Color literal", "export const A = () => <p>Visit Ste #1100 downtown.</p>;", "tsx"),
    ("comment_hex", "miss", "Color literal", '// #aabbcc is the old brand colour, kept for reference\nexport const B = () => <div className="p-4">hi</div>;', "tsx"),
    ("empty_payload", "exit:2", None, "", "tsx"),
    ("malformed_payload", "exit:2", None, "not json", "tsx"),
)

# Fail loudly on a malformed row rather than letting it silently misbehave at
# check-time: a typo'd expect value ("htt" instead of "hit") previously fell
# through to `want_hit = expect == "hit"` and degraded to a wrong-but-plausible
# "miss" expectation with no diagnostic — exactly the class of quiet drift this
# control exists to catch, reproduced in its own corpus.
for _name, _expect, _needle, _content, _ext in _VENDOR_CORPUS:
    assert _expect in ("hit", "miss") or re.match(r"^exit:\d+$", _expect), (
        f"_VENDOR_CORPUS[{_name!r}]: expect must be 'hit', 'miss', or 'exit:N', got {_expect!r}"
    )
del _name, _expect, _needle, _content, _ext


def _run_design_hook(hook, content, ext):
    """Execute a repo's vendored hook against one fixture, exactly as the
    PostToolUse harness would: content on disk, a JSON payload naming it on
    stdin. Returns (returncode, stdout+stderr)."""
    # path is captured, and the write wrapped in its own try, BEFORE the outer
    # try/finally that owns cleanup: writing after `delete=False` has already
    # created the file, so a write failure (disk full, I/O error) raised
    # between the `with` block and `path = tf.name` used to skip the
    # try/finally entirely, leaking the file with no path ever logged.
    with tempfile.NamedTemporaryFile(mode="w", suffix=f".{ext}", delete=False) as tf:
        path = tf.name
        try:
            tf.write(content)
        except Exception:
            os.unlink(path)
            raise
    try:
        payload = json.dumps({"tool_input": {"file_path": path}})
        proc = subprocess.run(
            ["bash", str(hook)], input=payload, capture_output=True, text=True, timeout=10,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    finally:
        os.unlink(path)


def _run_design_hook_raw_payload(hook, payload):
    """Same as _run_design_hook, but for the two cases that test malformed
    input itself rather than a file's content — there is no fixture file."""
    proc = subprocess.run(
        ["bash", str(hook)], input=payload, capture_output=True, text=True, timeout=10,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


@check("VNDR-01")
def _(r):
    if r.name == "design-system":
        return NA, "producer of the registry, not a consumer of its own hook"
    hook = r / ".claude" / "hooks" / "check-design-tokens.sh"
    if not hook.is_file():
        return NA, "design-system not installed"
    failed = []
    for name, expect, needle, content, ext in _VENDOR_CORPUS:
        try:
            if expect.startswith("exit:"):
                want_rc = int(expect.split(":", 1)[1])
                rc, out = _run_design_hook_raw_payload(hook, content)
                if rc != want_rc:
                    failed.append(f"{name} (expected exit {want_rc}, got {rc})")
                continue
            # Exit code is part of the behaviour being pinned, not just the
            # message: the hook's own contract is that exit 2 is the ONLY code
            # PostToolUse feeds back to the model, so a copy that writes the
            # right finding but exits 1 is functionally invisible — and would
            # have scored as a correct "hit" here if only the message text
            # were checked. want_rc mirrors that contract: 2 when a violation
            # should be reported, 0 when the file is clean.
            want_hit = expect == "hit"
            want_rc = 2 if want_hit else 0
            rc, out = _run_design_hook(hook, content, ext)
            got_hit = needle in out
            if got_hit != want_hit or rc != want_rc:
                failed.append(
                    f"{name} (expected {expect}/rc={want_rc}, got "
                    f"{'hit' if got_hit else 'miss'}/rc={rc})"
                )
        except Exception as e:
            # One fixture's subprocess timing out or erroring must not erase
            # the other 18 results into a bare "checker error" MANUAL at the
            # main() level — that would both hide which specific case broke
            # and (MANUAL doesn't count toward --fail-on) let a real
            # regression on the other cases go unreported alongside it.
            failed.append(f"{name} (error running fixture: {e})")
    if failed:
        return FAIL, f"{len(failed)}/{len(_VENDOR_CORPUS)} corpus cases wrong: " + "; ".join(failed)
    return PASS, f"all {len(_VENDOR_CORPUS)} corpus cases correct"


@check("AUTH-05")
def _(r):
    if r.name == "auth":
        return NA, "is the IdP, not a consumer"
    src = bff_source(r)
    if src is None:
        return NA, "no BFF"
    # Architecture gate: only a BFF that refreshes on the request path can hit
    # this at all. website/design-system seal a clock, not tokens — a transient
    # 5xx never touches them. Match the DEFINITION, not the name: website's
    # auth.ts mentions resolveSessionBearer in a comment ("hiro's equivalent"),
    # which a substring test reads as "has one".
    if not re.search(r"function\s+resolveSessionBearer", src):
        return NA, "session-as-clock BFF — no request-path refresh"
    # The behaviour, not the name: a "dead"/"unavailable" discrimination, and a
    # clear only on the dead branch. A bare `null` that clears on any failure is
    # the fleet-wide-logout bug.
    if "RefreshResult" not in src or '"unavailable"' not in src:
        return FAIL, "refresh collapses a transient 5xx into a session-clearing null"
    tf = bff_test(r)
    if tf is None:
        return FAIL, "no auth.test.ts pinning that a transient 5xx keeps the session"
    tsrc = tf.read_text()
    if not re.search(r"unavailable|transient|5xx|50\d", tsrc, re.IGNORECASE):
        return FAIL, "auth.test.ts never exercises the transient-5xx-keeps-session case"
    return PASS, "discriminates dead vs unavailable; 5xx survival pinned in test"


@check("AUTH-06")
def _(r):
    if r.name == "auth":
        return NA, "is the IdP, not a consumer"
    exports = bff_exports(r)
    if exports is None:
        return NA, "no BFF"
    login = login_route(r)
    # Idiom A (website, hero-template): an exported LoginTx + isLoginTx pair, and
    # the producer sealed with `satisfies LoginTx` so the two halves cannot drift.
    if "LoginTx" in exports and "isLoginTx" in exports:
        if "satisfies LoginTx" not in login:
            return FAIL, "login route seals the tx bare — not bound to LoginTx"
        return PASS, "LoginTx/isLoginTx centralised; producer bound via satisfies"
    # Idiom B (design-system): a typed sealer sealTx(data: TxData) does the same
    # binding through the parameter type.
    if "sealTx" in exports:
        if "sealTx(" not in login:
            return FAIL, "typed sealTx exported but the login route does not seal through it"
        return PASS, "typed sealTx(data: TxData) binds the producer"
    return FAIL, "tx type + validator not centralised in the server auth module"


@check("UI-03")
def _(r):
    # The hook itself, never its .test.ts (which sorts first and carries neither
    # the bare-return nor the breadcrumb).
    _rc, out = sh(r, "git ls-files | grep -E 'use-version-check\\.ts$'")
    if not out:
        return NA, "no version-check hook"
    hook = r / out.splitlines()[0]
    src = hook.read_text()
    # A bare `return` on a non-OK status is the silent hole: the endpoint is
    # visibly broken and the gate simply stops, with no trace.
    if re.search(r"if\s*\(\s*!res\.ok\s*\)\s*return\s*;", src):
        return FAIL, "a non-OK /version.json is silently ignored (bare return)"
    if not re.search(r"console\.(warn|error)", src):
        return FAIL, "version-check swallows failures with no breadcrumb"
    return PASS, "non-OK treated as failure; breadcrumb on a chronic break"


@check("SENTRY-01")
def _(r):
    _rc, exp = sh(r, "git grep -l 'SentryErrorBoundary' -- '*sentry*'")
    if not exp:
        return NA, "no Sentry error boundary"
    # Rendered, not merely exported — UI-01's lesson one layer down. The <JSX>
    # in a file that is not the sentry module itself or a test.
    _rc, used = sh(
        r,
        "git grep -l '<SentryErrorBoundary' -- '*.tsx' "
        "':(exclude)*sentry*' ':(exclude)*.test.tsx' ':(exclude)*.spec.tsx'",
    )
    if not used:
        return FAIL, "SentryErrorBoundary exported but never mounted — reports nothing"
    return PASS, f"mounted in {used.splitlines()[0]}"


def _sentry_browser(r):
    """The browser Sentry init file (lib/sentry.ts), or None. Excludes a
    server-side sentry-node.ts."""
    _rc, out = sh(r, "git ls-files | grep -E '(^|/)(ui/)?src/lib/sentry\\.ts$'")
    if not out:
        return None
    return r / out.splitlines()[0]


@check("SENTRY-02")
def _(r):
    f = _sentry_browser(r)
    if f is None:
        return NA, "no browser sentry init"
    src = f.read_text()
    if "parseRate" in src and "TRACES_SAMPLE_RATE" in src:
        return PASS, "traces rate via parseRate(env)"
    if re.search(r"tracesSampleRate\s*:\s*[0-9]", src):
        return FAIL, "tracesSampleRate hardcoded — not tunable without a rebuild"
    return MANUAL, "no parseRate and no literal rate found — verify"


@check("SENTRY-03")
def _(r):
    f = _sentry_browser(r)
    if f is None:
        return NA, "no browser sentry init"
    src = f.read_text()
    if re.search(r"release\s*:\s*(__APP_VERSION__|appVersion)", src):
        return PASS, "release == bundle version string"
    return FAIL, "Sentry release not tied to the bundle version string"


@check("SENTRY-04")
def _(r):
    f = r / "Dockerfile.prod"
    if not f.is_file():
        return NA, "no Dockerfile.prod"
    src = f.read_text()
    if "SENTRY_AUTH_TOKEN" not in src and "sentry_auth_token" not in src:
        return NA, "no Sentry source-map upload in the image"
    if not re.search(r"--mount=type=secret,id=sentry_auth_token", src):
        return FAIL, "sentry token not mounted as a BuildKit secret"
    if re.search(r"^\s*(ARG|ENV)\s+SENTRY_AUTH_TOKEN", src, re.MULTILINE):
        return FAIL, "SENTRY_AUTH_TOKEN declared as ARG/ENV — baked into a layer"
    return PASS, "token via BuildKit secret, never ARG/ENV"


@check("SENTRY-05")
def _(r):
    _rc, out = sh(r, "git ls-files | grep -E 'vite.config.ts$'")
    if not out:
        return NA, "no vite config"
    src = (r / out.splitlines()[0]).read_text()
    # Match the emitted annotation, not the prose about it: the trap comment
    # says "::error::" but never "::error title=Sentry", so this only fires on
    # the live console.error line.
    if "::error title=Sentry" in src:
        return FAIL, "non-rendering ::error:: annotation in the sourcemap errorHandler"
    return PASS, "no dead ::error:: annotation"


@check("SENTRY-06")
def _(r):
    # Only a runtime Node front has a server tier to report from. A static SPA
    # (design-system) has no server entry, so this does not apply.
    server = next(
        (r / c for c in ("ui/src/server.ts", "src/server.ts") if (r / c).is_file()),
        None,
    )
    if server is None:
        return NA, "no Node SSR server entry"
    src = server.read_text()
    # Init (the repo's initSentryServer helper or a direct server Sentry.init)
    # AND the fetch handler wrapped. Either half missing means SSR errors are
    # unreported — SENTRY-01's failure one tier up.
    if "initSentryServer" not in src and not re.search(r"Sentry\.init", src):
        return FAIL, "server entry does not initialize Sentry — SSR errors unreported"
    if "wrapFetchWithSentry" not in src:
        return FAIL, "fetch handler not wrapped — SSR errors escape uncaught"
    return PASS, "server-side init + wrapped fetch"


# Attacker-controllable FREE-STRING contexts that must reach a shell only via
# env:, never spliced into `run:`. This is deliberately narrow:
#
#   - inputs.* and github.head_ref carry arbitrary strings.
#   - github.event.*.{body,title,name,...} are the free-text/branch fields a
#     PR or comment author controls.
#
# It excludes what is NOT a shell-injection vector, so it does not false-fire on
# the safe splices auto-approve.yaml relies on: github.sha / github.ref_name /
# github.repository (trusted slugs), the numeric .number / .id, and
# steps.*.outputs (values the workflow itself produced and, for the verdict,
# pins to an enum before use). The deploy-summary bug this exists for was
# inputs.gh_env spliced into a heredoc — squarely inside this set.
_UNTRUSTED_RUN = re.compile(
    r"\$\{\{\s*(github\.head_ref\b|inputs\.[A-Za-z0-9_]+"
    r"|github\.event\.[A-Za-z0-9_.]*(body|title|name|ref|label|message|login|email|description))"
)


@check("CI-13")
def _(r):
    wfs = workflows(r)
    if not wfs:
        return NA, "no workflows"
    hits = []
    for wf in wfs:
        try:
            doc = yaml.safe_load(wf.read_text())
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        for job in (doc.get("jobs") or {}).values():
            if not isinstance(job, dict):
                continue
            for step in job.get("steps") or []:
                if not isinstance(step, dict):
                    continue
                run = step.get("run")
                if isinstance(run, str) and _UNTRUSTED_RUN.search(run):
                    hits.append(f"{wf.name}:{(step.get('name') or 'run')}")
    if hits:
        return FAIL, "untrusted context spliced into run: " + "; ".join(sorted(set(hits))[:3])
    return PASS, "untrusted context reaches shell via env: only"


@check("HLT-04")
def _(r):
    if has_go(r):
        _rc, files = sh(
            r,
            "git grep -lI -E 'NewReadyHandler|/readyz|health probe|probe failed' -- '*.go'",
        )
        if not files:
            return NA, "no readyz handler found"
        for rel in files.splitlines():
            if re.search(r"slog\.(Error|Warn)\(", (r / rel).read_text()):
                return PASS, "readyz probe failure logged (slog)"
        return FAIL, "no failure log on the readyz probe path — a 503 with an empty log"
    # Node front: the readyz route / server health module.
    _rc, files = sh(r, "git ls-files | grep -E 'readyz|server/health'")
    if not files:
        return NA, "no readyz handler"
    for rel in files.splitlines():
        p = r / rel
        if p.is_file() and re.search(r"console\.(error|warn)", p.read_text()):
            return PASS, "readyz probe failure logged (console)"
    return FAIL, "no failure log on the readyz probe path — a 503 with an empty log"


@check("UI-02")
def _(r):
    """The commit actually reaches the version generator in the prod build.

    UI-01 proves the gate is mounted. This proves it can ever FIRE, which is a
    different question and the one that was silently answered "no" in 2 of the
    4 repos that had a gate: the generator falls back to git, .dockerignore
    excludes .git, and nothing passed a SHA — so the image stamped "dev" into
    both the baked and the served version. They agree forever. It compiles,
    tests, and deploys green while doing nothing.
    """
    gen = [f for f in sh(r, "git ls-files")[1].splitlines() if "generate-version" in f]
    if not gen:
        return NA, "no version generator (see UI-01)"
    df = r / "Dockerfile.prod"
    if not df.is_file():
        return NA, "no Dockerfile.prod"
    dft = df.read_text()
    # Only a build that cannot reach .git depends on the arg. If the context
    # keeps .git, the generator's own fallback finds the commit and there is
    # nothing to pass.
    di = r / ".dockerignore"
    if not di.is_file() or not re.search(r"(?m)^\.git/?$", uncommented(di.read_text())):
        return NA, ".git in build context — generator resolves the commit itself"
    # Ask the GENERATOR which name it reads. Wiring an ARG it does not read
    # leaves the gate exactly as dead while looking fixed — that happened here,
    # and only a test caught it.
    wants = set(re.findall(r"process\.env\.([A-Z_]+SHA)", (r / gen[0]).read_text()))
    if not wants:
        return MANUAL, f"{gen[0]} reads no *_SHA env — how does it learn the commit?"
    armed = {w for w in wants if re.search(rf"(?m)^ARG\s+{w}\b", dft)}
    if not armed:
        return FAIL, f"Dockerfile.prod passes none of {','.join(sorted(wants))} — every build stamps 'dev'"
    passed = set()
    for wf in workflows(r):
        for w in armed:
            if re.search(rf"{w}=\$\{{\{{\s*github\.sha\s*\}}\}}", wf.read_text()):
                passed.add(w)
    if not passed:
        return FAIL, f"ARG {','.join(sorted(armed))} declared but no workflow passes github.sha"
    return PASS, f"{','.join(sorted(passed))} reaches {gen[0]}"


@check("DOC-06")
def _(r):
    TEST_LINE = "undo this for a reason this comment prevents"
    # A sentence from the guidance body that the AGENTS.md pointer must NOT
    # carry — its presence means the full guide grew back beside the pointer.
    BODY_SENTINEL = "Comment rot is not untidiness"
    rule = r / ".claude" / "rules" / "comments.md"
    if not rule.is_file():
        return FAIL, "no .claude/rules/comments.md"
    if TEST_LINE not in rule.read_text():
        return FAIL, "comments.md lacks the one-line test"
    f = r / "AGENTS.md"
    if not f.is_file():
        return FAIL, "no AGENTS.md (see DOC-04)"
    t = f.read_text()
    if "comments.md" not in t or TEST_LINE not in t:
        return FAIL, "AGENTS.md lacks the pointer + one-line test"
    if BODY_SENTINEL in t:
        return FAIL, "full guidance grew back beside the pointer"
    return PASS, ""


@check("LIC-01")
def _(r):
    # GitHub detects LICENSE/LICENCE/COPYING with an optional extension.
    if not any((r / n).is_file() for n in
               ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "COPYING")):
        return FAIL, "no LICENSE at the repo root"
    cfg = r / ".pre-commit-config.yaml"
    if not cfg.is_file():
        return FAIL, "no .pre-commit-config.yaml"
    try:
        raw = cfg.read_text()
    except (OSError, UnicodeDecodeError) as e:
        return MANUAL, f"cannot read .pre-commit-config.yaml: {e}"
    # Grep the raw text rather than parsing: the hook is identified by id and
    # the flag by its literal spelling, and a YAML walk would have to guess
    # which of several repos/hooks entries owns them.
    if "insert-license" not in raw:
        return FAIL, "no insert-license hook"
    # The stamp template must not BE the LICENSE — insert-license's default is
    # LICENSE.txt, which both collides with GitHub's detection and would prefix
    # every source file with the full notice.
    if "--license-filepath" not in raw:
        return FAIL, "insert-license does not set --license-filepath (defaults to LICENSE.txt)"
    # Pull the VALUE rather than pattern-matching one spelling. All of these are
    # ordinary YAML and argparse, and an earlier line-anchored regex caught only
    # the first: `- --license-filepath=X`, `args: [--license-filepath=X, ...]`,
    # `- "--license-filepath=X"`, and the split `- --license-filepath` / `- X`.
    # `(?:-\s+)?` absorbs the YAML list dash in the split form, where the value
    # sits on the NEXT line as its own item.
    values = re.findall(
        r"--license-filepath[=\s]+(?:-\s+)?[\"\']?([^\"\',\]\s]+)", raw)
    for v in values:
        if re.fullmatch(r"LICEN[SC]E(\.[A-Za-z]+)?|COPYING", pathlib.Path(v).name):
            return FAIL, f"insert-license stamps {v}, the repo LICENSE; use a separate header template"
    if not values:
        return MANUAL, "could not read --license-filepath's value"
    # --use-current-year, chosen over Chromium's "never touch the year".
    # That convention prevents annual churn but freezes whatever year a file
    # was first stamped with, and this family's 414 headers said 2024 for code
    # whose earliest commit is 2026. A frozen wrong year beats an annual diff
    # only if the frozen year was right. (--use-current-year implies
    # --allow-past-years, so accept either spelling.)
    if not ("--use-current-year" in raw or "--allow-past-years" in raw):
        return FAIL, "insert-license sets neither --use-current-year nor --allow-past-years"
    return PASS, ""


# LIC-02 judges only OUR OWN stamp. Scoping by holder rather than by path is
# what keeps the check safe across repos: a vendored or generated file may
# legitimately carry `Copyright (c) 2016 Google Inc.`, and a check that called
# that a stale year would demand someone rewrite a third party's copyright to
# go green.
_LIC_HOLDER = r"A\.I\. Hero, Inc\."

# A cheap skip-list for paths nothing of ours should be stamped in. It is a
# narrowing convenience, NOT a correctness guarantee: it does not detect drift
# from the hook's own excludes in either direction, and it is this repo's
# layout. The holder match above is what makes the check correct elsewhere.
_LIC_SKIP = ("schema/gen/", "ui/src/gen/", "ui/src/routeTree.gen.ts",
             "ui/src/components/ui/", "ui/src/components/blocks/",
             ".claude/hooks/", "node_modules/", "ui/.output/", ".venv/")


@check("LIC-02")
def _(r):
    if not any((r / n).is_file() for n in
               ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "COPYING")):
        return NA, "no LICENSE (LIC-01 owns the wiring)"
    rc, out = sh(r, r"git ls-files '*.go' '*.ts' '*.tsx' '*.py' '*.sh'")
    if rc != 0:
        return MANUAL, "git ls-files failed"
    year = str(datetime.now().year)
    stale = []
    for rel in out.splitlines():
        if not rel or any(rel.startswith(x) or f"/{x}" in rel for x in _LIC_SKIP):
            continue
        f = r / rel
        try:
            head = f.read_text(errors="replace")[:400]
        except OSError:
            continue
        m = re.search(
            rf"Copyright \(c\) (\d{{4}}(?:\s*-\s*\d{{4}})?) {_LIC_HOLDER}", head)
        # A file with no stamp of OURS is LIC-01's problem (no hook, or the hook
        # has not run); this check only judges the year of stamps that exist.
        if m and m.group(1) != year:
            stale.append(f"{rel}:{m.group(1)}")
    if not stale:
        return PASS, ""
    shown = ", ".join(stale[:3])
    more = f" (+{len(stale) - 3} more)" if len(stale) > 3 else ""
    return FAIL, f"{len(stale)} file(s) not {year}: {shown}{more}"


@check("ARCH-01")
def _(r):
    if (r / "DESIGN.md").is_file():
        return PASS, ""
    # Distinguish "never written" from "written under the pre-rename name".
    # Both FAIL, but they are different jobs: one is a bootstrap, the other a
    # git mv. Collapsing them sends someone to `sync` to author a file that
    # already exists, and the duplicate is what actually lands.
    #
    # Kept after the fleet migrated, for a repo that joins later carrying the
    # old name. Such a repo now also fails PLACE-04, since ARCHITECTURE is no
    # longer an allowlisted root document — that pair is expected, and THIS
    # message is the authoritative remedy. Renaming satisfies both.
    if (r / "ARCHITECTURE.md").is_file():
        return FAIL, "still ARCHITECTURE.md — git mv to DESIGN.md (H1 too)"
    return FAIL, "missing — run hero-skills:architecture sync"


@check("ARCH-02")
def _(r):
    f = r / "DESIGN.md"
    if not f.is_file():
        return NA, "no DESIGN.md (ARCH-01 owns existence)"
    try:
        lines = f.read_text().splitlines()
    except UnicodeDecodeError:
        # The grammar's required '·' is the exact byte a Latin-1 round-trip
        # breaks — this mojibake IS a malformed anchor, not a checker error.
        return FAIL, "not valid UTF-8 — the anchor's '·' must be UTF-8 encoded"
    # Line 3, fixed grammar, strict on purpose — see ARCH-02's why.
    if len(lines) < 3 or not (
        m := re.match(
            r"^> Last updated: \d{4}-\d{2}-\d{2} · Source ref: ([0-9a-f]{40})$",
            lines[2],
        )
    ):
        return FAIL, "missing/malformed anchor on line 3"
    # Bind git to THIS directory before trusting its answer: upward .git
    # discovery from a non-clone would resolve the SHA against an ancestor
    # repo and report a false PASS.
    rc, top = sh(r, "git rev-parse --show-toplevel")
    if rc != 0 or pathlib.Path(top) != r.resolve():
        return MANUAL, "not a git clone — anchor unverifiable"
    rc, _out = sh(r, f"git cat-file -e {m.group(1)}^{{commit}}")
    if rc != 0:
        return MANUAL, "anchor SHA does not resolve to a commit in this clone (see ARCH-02's why)"
    return PASS, ""


# The skill's section contract. Order is not checked — only membership: a
# reordered file still gives every consumer the section it navigates by, and
# failing on order would make a cosmetic edit look like a structural defect.
_ARCH_CORE = ("Overview", "Tech stack", "Codemap", "Boundaries", "Invariants",
              "Decisions")
_ARCH_PRODUCT = ("Users", "Flows", "Interaction standards")


@check("ARCH-03")
def _(r):
    f = r / "DESIGN.md"
    if not f.is_file():
        return NA, "no DESIGN.md (ARCH-01 owns existence)"
    try:
        text = f.read_text()
    except UnicodeDecodeError:
        return FAIL, "not valid UTF-8"
    # Same spelling as DOC-01 (\s+, then strip), not `^## (.+?)\s*$`: CommonMark
    # allows a tab or several spaces after the hashes, and the tighter pattern
    # reports "missing section(s): Tech stack" against a file where the heading
    # is plainly there — the failure that sends someone hunting the checker.
    have = {h.strip() for h in re.findall(r"^##\s+(.+)$", text, re.M)}
    missing = [s for s in _ARCH_CORE if s not in have]
    # A user-facing surface is what makes the product sections required, and
    # the family spells it two ways: an app repo puts the front end in `ui/`,
    # while a repo that IS the front end (design-system) has `src/routes/` at
    # the top. Keying on `ui/` alone silently exempted the second shape —
    # design-system ships a registry site with routes and would have been
    # told it needs no Users or Flows.
    stray = []
    if (r / "ui").is_dir() or (r / "src" / "routes").is_dir():
        missing += [s for s in _ARCH_PRODUCT if s not in have]
    else:
        # Present at all is the failure, filled or empty: a repo with no
        # surface carrying `## Users` claims one, and every consumer that
        # navigates by the skeleton believes it.
        stray = [s for s in _ARCH_PRODUCT if s in have]
    # Report both causes in one pass. Returning early on stray discarded an
    # already-computed `missing`, so deleting the stray heading surfaced five
    # core sections nobody had been told about — a second full round trip for
    # evidence the first run was holding.
    detail = "; ".join(
        d for d in (
            f"missing section(s): {', '.join(missing)}" if missing else "",
            f"no user-facing surface, so drop: {', '.join(stray)}" if stray else "",
        ) if d
    )
    return (FAIL, detail) if detail else (PASS, "")


# Where the register lives: the fleet's register checkout (FLEET.md
# `register:`), never a repo. So every repo that carries one of these is
# carrying a copy — including the template the register used to live in.
# Presence list — deliberately NOT REGISTER_FILES, which is the content-grep
# exclusion set. The two overlap but answer different questions, and merging
# them would put a file in one job because it belonged in the other.
_REGISTER_ARTIFACTS = ("CONTROLS.yaml", "CHECKS.yaml", "CONSISTENCY.md",
                       "scripts/audit.py", "scripts/consistency.py",
                       ".claude/skills/consistency-audit")


@check("REG-01")
def _(r):
    # is_symlink() as well as exists(): a broken symlink is still a copy this
    # repo declares it owns, and exists() alone reads it as clean.
    found = [p for p in _REGISTER_ARTIFACTS
             if (r / p).exists() or (r / p).is_symlink()]
    if not found:
        return PASS, ""
    home = REGISTER or "hero-skills (engine) and the fleet's register checkout"
    return FAIL, f"carries register copy: {', '.join(found)} — the register lives in {home}"


# ── The protobuf wire contract ───────────────────────────────────────────────
# Gated on .proto sources existing, NOT on has_go: the question is whether the
# repo HAS a generated contract, and a repo could carry one without Go (or Go
# without protos). CHECKS.yaml's `schema` group says the same thing in the
# register; audit.py ignores applies_to, so the gate has to live here too.


def _has_protos(repo):
    return bool(list((repo / "schema").glob("**/*.proto"))) if (repo / "schema").is_dir() else False


def _bufgen(repo):
    """schema/buf.gen.yaml text, or "". Read as text, not parsed: the check is
    about how a plugin reference is SPELLED (bare `remote:` vs tagged vs
    `local:`), and yaml.safe_load normalises away exactly that distinction."""
    f = repo / "schema" / "buf.gen.yaml"
    return f.read_text() if f.is_file() else ""


@check("SCHEMA-01")
def _(r):
    if not _has_protos(r):
        return NA, "no .proto sources"
    missing = [n for n in ("buf.yaml", "buf.gen.yaml") if not (r / "schema" / n).is_file()]
    if missing:
        return FAIL, "missing " + ", ".join("schema/" + n for n in missing)
    stale = [
        n
        for n in ("buf.yaml", "buf.gen.yaml")
        if not re.search(r"^version:\s*v2\s*$", (r / "schema" / n).read_text(), re.M)
    ]
    return (PASS, "") if not stale else (FAIL, "not version: v2 — " + ", ".join(stale))


def _regenerates(repo, text):
    """Does this workflow text trigger codegen — directly or through `just`?

    Matching only a literal `buf generate` would fail the repos doing it right.
    JUST-01 requires CI to invoke gates through the Justfile precisely so CI and
    the runner cannot spell them differently and drift, so hero-template's job
    says `just proto-gen`. A checker that demands the raw command rewards
    restating it in the workflow — pushing repos toward the duplication another
    control exists to prevent.
    """
    if "buf generate" in text:
        return True
    just = repo / "Justfile"
    if not just.is_file():
        return False
    body = just.read_text()
    for recipe in set(re.findall(r"\bjust\s+([a-z][a-z0-9-]*)", text)):
        # Recipe body = the header line through the last indented line under it.
        m = re.search(rf"^{re.escape(recipe)}:.*?(?=^\S|\Z)", body, re.M | re.S)
        if m and "buf generate" in m.group(0):
            return True
    return False


@check("SCHEMA-02")
def _(r):
    if not _has_protos(r):
        return NA, "no .proto sources"
    # Both halves must appear in the SAME workflow file: a repo that regenerates
    # in one job and happens to diff something unrelated in another has no
    # freshness gate, and matching across files would pass it.
    regen = False
    for f in workflows(r):
        text = uncommented(f.read_text())
        if not _regenerates(r, text):
            continue
        regen = True
        if re.search(r"git diff\b.*(--quiet|--exit-code)", text):
            return PASS, f.name
    if regen:
        return FAIL, "regenerates the contract but never diffs the committed output"
    return FAIL, "no workflow regenerates the contract to check it is in sync"


@check("SCHEMA-03")
def _(r):
    if not _has_protos(r):
        return NA, "no .proto sources"
    text = _bufgen(r)
    if not text:
        return NA, "no schema/buf.gen.yaml (SCHEMA-01 owns existence)"
    # ANY remote ref, tagged or not. A tag looks like a pin and is not one: the
    # BSR publishes revisions underneath a version tag and buf.lock does not
    # cover plugins, so the ref still names something that can change. And
    # `remote:` executes off-machine, which no tag addresses at all. Matching
    # only untagged refs (what this did until 2026-07-25) blessed hiro's
    # `:v1.36.11` as compliant while it still shipped the descriptor set to
    # buf.build on the path that generates code compiled into the service.
    remotes = re.findall(r"^\s*-?\s*remote:\s*(\S+)", text, re.M)
    return (PASS, "") if not remotes else (FAIL, "remote plugin (use local:): " + ", ".join(remotes))


@check("SCHEMA-04")
def _(r):
    if not _has_protos(r):
        return NA, "no .proto sources"
    text = _bufgen(r)
    if not text:
        return NA, "no schema/buf.gen.yaml (SCHEMA-01 owns existence)"
    outs = re.findall(r"^\s*out:\s*(\S+)", text, re.M)
    if not outs:
        return MANUAL, "no `out:` found — verify by hand"
    ts = [o for o in outs if "ui/src/gen" in o]
    if ts:
        return PASS, ""
    # No TS plugin at all is a different shape from one aimed elsewhere, and
    # only the latter is what this check is about.
    if not re.search(r"protoc-gen-es|connect-(es|query)", text):
        return NA, "no TypeScript plugin configured"
    return FAIL, "TS generated outside the UI tree: " + ", ".join(o for o in outs if "gen" in o)


_SHARED_WORKFLOW_OWNER = "hero-skills"
_PLUGIN_ASSETS = pathlib.Path(os.environ.get("HERO_SKILLS_PLUGIN")
                              or os.path.expanduser("~/.claude/plugins/hero-skills")) / "assets"


class Unreadable(Exception):
    """A file a checker must read cannot be parsed — the verdict is MANUAL
    naming the file, never a PASS built on an empty document."""


def _wf_doc(path):
    try:
        doc = yaml.safe_load(path.read_text())
    except (yaml.YAMLError, OSError, UnicodeDecodeError) as e:
        raise Unreadable(f"{path.name}: {e}") from e
    if not isinstance(doc, dict):
        raise Unreadable(f"{path.name}: top level is {type(doc).__name__}")
    return doc


def _wf_on(doc):
    """The `on:` block as a dict. PyYAML 1.1 reads a bare `on` key as boolean
    True, so doc.get("on") sees nothing and passes every repo; GitHub also
    accepts `on: push` and `on: [push, pull_request]`."""
    on = doc.get("on") or doc.get(True) or {}
    if isinstance(on, str):
        return {on: None}
    if isinstance(on, list):
        return {k: None for k in on}
    return on if isinstance(on, dict) else {}


def _hook_segment(pc, hook_id):
    """The text of one pre-commit hook entry, from its `id:` to the next hook
    or repo. Matching the whole config attributes another hook's args to
    this one."""
    m = re.search(rf"id:\s*{re.escape(hook_id)}\b.*?(?=\n\s*-\s*id:|\n-\s*repo:|\Z)", pc, re.S)
    return m.group(0) if m else ""


def _matches_reference(mine, ref, extract=None):
    """A vendored artifact equals its source. MANUAL when the source is not
    on this machine (nothing to compare against is not a pass); FAIL when the
    artifact is missing or differs. `extract` pulls the vendored part out of a
    larger file (a section of AGENTS.md)."""
    if not ref.is_file():
        return MANUAL, f"reference absent: {ref}"
    if not mine.is_file():
        return FAIL, f"missing {mine.name}"
    if extract is None:
        return (PASS, "") if mine.read_bytes() == ref.read_bytes() else (FAIL, f"differs from {ref.name}")
    got = extract(mine.read_text())
    if got is None:
        return FAIL, "section absent"
    return (PASS, "") if got.strip() == ref.read_text().strip() else (FAIL, "differs from the installed asset")


_FROM_RE = re.compile(r"^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)(?:\s+AS\s+(\S+))?", re.I | re.M)
_IMAGE_RE = re.compile(r"^\s*image:\s*['\"]?(\S+?)['\"]?\s*$", re.M)


def _image_refs(path):
    """(name, tag) for every pullable image reference in a Dockerfile or
    compose file — name is the last path segment, tag "" when absent. Stage
    names, scratch, variables and digest-pinned refs are not references to a
    tag and are dropped."""
    text = path.read_text()
    if path.name.startswith("Dockerfile"):
        from_lines = list(_FROM_RE.finditer(text))
        stages = {m.group(2) for m in from_lines if m.group(2)}
        refs = [m.group(1) for m in from_lines]
    else:
        stages = set()
        refs = _IMAGE_RE.findall(uncommented(text))
    out = []
    for ref in refs:
        if ref in stages or ref == "scratch" or "$" in ref or "@sha256:" in ref:
            continue
        name, _, tag = ref.rsplit("/", 1)[-1].partition(":")
        out.append((name, tag))
    return out


def _image_files(r):
    return list(r.glob("Dockerfile*")) + list(r.glob("docker-compose*.y*ml"))


def _json_file(path):
    """JSON with `//` line comments stripped — VS Code reads its own files as
    JSONC, so a commented extensions.json is valid to the editor."""
    text = re.sub(r"^\s*//.*$", "", path.read_text(), flags=re.M)
    return json.loads(text)


@check("STRUCT-10")
def _(r):
    if not yml(r, "docker-compose.dev").is_file():
        return NA, "no dev stack"
    return (PASS, "") if tracked(r, ".env.example") else (FAIL, "root .env.example not tracked")


_GENERATED = ("schema/gen", "ui/src/gen", "ui/src/routeTree.gen.ts")


@check("STRUCT-11")
def _(r):
    present = [g for g in _GENERATED if (r / g).exists()]
    if not present:
        return NA, "no generated code"
    f = r / ".claude" / "settings.json"
    if not f.is_file():
        return FAIL, "no .claude/settings.json"
    try:
        deny = _json_file(f).get("permissions", {}).get("deny", [])
    except (json.JSONDecodeError, OSError, AttributeError) as e:
        return FAIL, f"settings.json: {e}"
    # Only a single-slash path is anchored to the settings source (the repo
    # root). `Read(./x)` is relative to the session's cwd, so it denies
    # nothing once an agent has cd'd into ui/ — the form the template
    # shipped for a month.
    anchored = [d for d in deny if re.match(r"Read\(/[^/]", d)]
    missing = [g for g in present if not any(g in d for d in anchored)]
    relative = [d for d in deny if d.startswith("Read(./")]
    if missing:
        why = " (cwd-relative `./` entries do not count)" if relative else ""
        return FAIL, "no root-anchored deny for " + ", ".join(missing) + why
    return PASS, ""


@check("CI-20")
def _(r):
    if TEMPLATE is None:
        return NA, "no fleet template to compare against"
    if r.name in (TEMPLATE, _SHARED_WORKFLOW_OWNER):
        return NA, "reference / shared workflow owner"
    mine = r / ".github" / "workflows" / "auto-approve.yaml"
    if not mine.is_file():
        return NA, "no auto-approve caller"
    return _matches_reference(mine, repo_path(TEMPLATE) / ".github" / "workflows" / "auto-approve.yaml")


@check("CI-21")
def _(r):
    wfs = workflows(r)
    if not wfs:
        return NA, "no workflows"
    bad = []
    try:
        for w in wfs:
            pr = _wf_on(_wf_doc(w)).get("pull_request")
            if isinstance(pr, dict) and ("paths" in pr or "paths-ignore" in pr):
                bad.append(w.name)
    except Unreadable as e:
        return MANUAL, str(e)
    return (FAIL, "paths filter on pull_request: " + ", ".join(bad)) if bad else (PASS, "")


_FLEET = {}   # family-wide caches; cleared on snapshot entry and exit
_USES_RE = re.compile(r"uses:\s*([\w.-]+/[\w./-]+)@([0-9a-f]{40})\s*#\s*(v?[\d.]+)")


def _action_pins():
    """(action, comment) -> {sha: set(repos)} across the family."""
    if "pins" not in _FLEET:
        pins = {}
        for rn in FAMILY:
            for w in workflows(repo_path(rn)):
                for m in _USES_RE.finditer(w.read_text()):
                    action, sha, ver = m.groups()
                    action = action.split("/.github/")[0]
                    pins.setdefault((action, ver), {}).setdefault(sha, set()).add(rn)
        _FLEET["pins"] = pins
    return _FLEET["pins"]


@check("CI-22")
def _(r):
    if not workflows(r):
        return NA, "no workflows"
    bad = []
    for (action, ver), shas in _action_pins().items():
        if len(shas) < 2:
            continue
        top = max(len(v) for v in shas.values())
        for sha, repos in shas.items():
            if r.name in repos and len(repos) < top:
                bad.append(f"{action} {ver}@{sha[:7]} (majority differs)")
    return (FAIL, "; ".join(bad)) if bad else (PASS, "")


@check("CI-23")
def _(r):
    if not _ships_image(r):
        return NA, "no image"
    try:
        for w in workflows(r):
            text = w.read_text()
            if "schedule" in _wf_on(_wf_doc(w)) and ("trivy-action" in text or "scout-action" in text):
                return PASS, w.name
    except Unreadable as e:
        return MANUAL, str(e)
    return FAIL, "no scheduled scan workflow"


@check("GATE-07")
def _(r):
    if not has_go(r):
        return NA, "no Go"
    hits = [w.name for w in workflows(r) if "tidy -diff" in uncommented(w.read_text())]
    return (PASS, ", ".join(hits)) if hits else (FAIL, "no workflow runs go mod tidy -diff")


@check("GATE-08")
def _(r):
    seg = _hook_segment(uncommented(precommit(r)), "markdownlint")
    if not seg:
        return NA, "no markdownlint hook"
    cfg = [f for f in (".markdownlint.yaml", ".markdownlint.yml", ".markdownlint.json",
                       ".markdownlint-cli2.yaml", ".markdownlint-cli2.jsonc") if (r / f).is_file()]
    if not cfg:
        return FAIL, "no .markdownlint config"
    if "--disable" in seg:
        return FAIL, f"{cfg[0]} exists but rules are also disabled inline"
    return PASS, cfg[0]


@check("GATE-09")
def _(r):
    if not has_ui(r):
        return NA, "no UI"
    root = r / "ui" if (r / "ui" / "tsconfig.json").is_file() else r
    tsconfig = root / "tsconfig.json"
    if not tsconfig.is_file():
        return NA, "no tsconfig"
    if '"references"' not in tsconfig.read_text():
        return NA, "single-project tsconfig; --noEmit is fine here"
    blob = "\n".join(f.read_text() for f in (r / "Justfile", root / "package.json") if f.is_file())
    cmds = re.findall(r"\btsc\b[^\n\"&|;]*", uncommented(blob))
    if not cmds:
        return NA, "no tsc invocation found"
    bad = [c.strip() for c in cmds if not re.search(r"\s(-b|--build)\b", c)]
    return (FAIL, "solution file but: " + "; ".join(bad)) if bad else (PASS, "")


@check("CTR-09")
def _(r):
    if not _ships_image(r):
        return NA, "no image"
    bad = [f"{f.name}: {name}:{tag or '<untagged>'}" for f in _image_files(r)
           for name, tag in _image_refs(f) if not tag or tag == "latest"]
    return (FAIL, "; ".join(bad)) if bad else (PASS, "")


@check("CTR-10")
def _(r):
    f = r / "dev.sh"
    if not f.is_file():
        return NA, "no dev.sh"
    return (PASS, "") if re.search(r"^die\(\)", f.read_text(), re.M) else (FAIL, "no die(); wait loops fall through")


@check("CTR-11")
def _(r):
    majors = {re.match(r"\d*", tag).group(0) for f in _image_files(r)
              for name, tag in _image_refs(f) if name == "mongo"}
    if not majors:
        return NA, "no mongo"
    if len(majors) > 1:
        return FAIL, "mongo majors " + "/".join(sorted(majors))
    units = {f.name: uncommented(f.read_text()) for f in (r / "dev.sh", yml(r, "docker-compose.prod")) if f.is_file()}
    units = {n: t for n, t in units.items() if "mongod" in t or "mongo:" in t}
    if not units:
        return NA, "no mongod run by dev.sh or the prod compose"
    missing = [n for n, t in units.items() if "--replSet" not in t]
    if missing:
        return FAIL, "no --replSet in " + ", ".join(missing)
    return PASS, f"mongo:{majors.pop()} x{len(units)}"


@check("UI-04")
def _(r):
    if not has_ui(r) or not _ships_image(r):
        return NA, "no UI image"
    f = r / ".dockerignore"
    if not f.is_file():
        return NA, "no .dockerignore (STRUCT-01)"
    return (PASS, "") if "version.json" in uncommented(f.read_text()) else (FAIL, "version.json not excluded")


@check("PRE-06")
def _(r):
    seg = _hook_segment(uncommented(precommit(r)), "semgrep")
    if not seg:
        return NA, "no semgrep hook"
    missing = [w for w in ("--config=auto", "--error", "--skip-unknown-extensions") if w not in seg]
    return (FAIL, "missing " + " ".join(missing)) if missing else (PASS, "")


def _hook_revs():
    """hook repo URL -> {repo: rev} across the family, plus the repos whose
    config could not be parsed (they are not voters, and PRE-07 says so)."""
    if "revs" not in _FLEET:
        revs, broken = {}, {}
        for rn in FAMILY:
            text = precommit(repo_path(rn))
            if not text:
                continue
            try:
                for rep in (yaml.safe_load(text) or {}).get("repos", []):
                    if isinstance(rep, dict) and rep.get("rev"):
                        revs.setdefault(rep["repo"], {})[rn] = rep["rev"]
            except (yaml.YAMLError, AttributeError) as e:
                broken[rn] = str(e).splitlines()[0]
        _FLEET["revs"], _FLEET["revs-broken"] = revs, broken
    return _FLEET["revs"], _FLEET["revs-broken"]


@check("PRE-07")
def _(r):
    if not precommit(r):
        return NA, "no pre-commit"
    revs, broken = _hook_revs()
    if r.name in broken:
        return MANUAL, f".pre-commit-config.yaml unparsable: {broken[r.name]}"
    behind = []
    for url, by_repo in revs.items():
        if r.name not in by_repo or len(by_repo) < 3:
            continue
        counts = {}
        for rev in by_repo.values():
            counts[rev] = counts.get(rev, 0) + 1
        majority = max(counts, key=lambda k: (counts[k], _semver(k) or ()))
        mine, top = _semver(by_repo[r.name]), _semver(majority)
        if mine and top and mine < top:
            behind.append(f"{url.rsplit('/', 1)[-1]} {by_repo[r.name]} < {majority}")
    note = f" (not voting: {', '.join(sorted(broken))})" if broken else ""
    return (FAIL, "; ".join(behind) + note) if behind else (PASS, note.strip())


@check("JUST-05")
def _(r):
    jf = r / "Justfile"
    if not jf.is_file() or not yml(r, "docker-compose.dev").is_file():
        return NA, "no dev stack"
    # Raw text: uncommented() would blank the recipe's shebang line and the
    # body regex, which needs an indented first line, would see no recipe.
    m = re.search(r"^health[^\n]*:\n((?:[ \t]+[^\n]*\n?)+)", jf.read_text(), re.M)
    if not m:
        return NA, "no health recipe"
    body = "\n".join(l for l in m.group(1).splitlines() if not l.lstrip().startswith("#"))
    return (PASS, "") if re.search(r'\.status|"ok"', body) else (FAIL, "checks HTTP code only")


@check("REL-01")
def _(r):
    hits = tracked(r, "CHANGELOG*", "changelog*", "VERSION", "VERSION.*", "version.md")
    return (FAIL, ", ".join(hits)) if hits else (PASS, "")


# Which extension a repo needs, by what it runs. One row per tool; the
# predicate is the same signal the hooks/CI checks already use.
_IDE_FLOOR = (
    (lambda r, pc: True, "johnpapa.vscode-cloak"),
    (lambda r, pc: True, "redhat.vscode-yaml"),
    (lambda r, pc: has_go(r), "golang.go"),
    (lambda r, pc: has_node(r), "dbaeumer.vscode-eslint"),
    (lambda r, pc: "tailwindcss" in _npm_versions(r), "bradlc.vscode-tailwindcss"),
    (lambda r, pc: (r / "schema" / "buf.yaml").is_file(), "bufbuild.vscode-buf"),
    (lambda r, pc: _ships_image(r), "ms-azuretools.vscode-containers"),
    (lambda r, pc: "hadolint" in pc, "exiasr.hadolint"),
    (lambda r, pc: "shellcheck" in pc or (r / "dev.sh").is_file() or (r / ".claude" / "hooks").is_dir(),
     "timonwong.shellcheck"),
    (lambda r, pc: "markdownlint" in pc, "davidanson.vscode-markdownlint"),
    (lambda r, pc: bool(workflows(r)), "github.vscode-github-actions"),
    (lambda r, pc: (r / "Justfile").is_file(), "skellock.just"),
    (lambda r, pc: "ruff" in pc or has_python(r), "ms-python.python"),
    (lambda r, pc: "ruff" in pc or has_python(r), "charliermarsh.ruff"),
)


@check("IDE-01")
def _(r):
    f = r / ".vscode" / "extensions.json"
    if not tracked(r, ".vscode/extensions.json"):
        gi = (r / ".gitignore").read_text() if (r / ".gitignore").is_file() else ""
        why = "; .gitignore excludes the .vscode/ directory" if re.search(r"^\.vscode/?\s*$", gi, re.M) else ""
        return FAIL, "no tracked .vscode/extensions.json" + why
    try:
        recs = set(_json_file(f).get("recommendations", []))
    except (json.JSONDecodeError, OSError, AttributeError) as e:
        return FAIL, f"extensions.json: {e}"
    pc = uncommented(precommit(r))
    if "prettier" not in pc and "esbenp.prettier-vscode" in recs:
        return FAIL, "recommends prettier, which no hook runs here"
    missing = sorted({ext for pred, ext in _IDE_FLOOR if pred(r, pc)} - recs)
    return (FAIL, "missing " + " ".join(missing)) if missing else (PASS, "")


def _fleet_section(text):
    i = text.find("\n## Fleet\n")
    if i < 0:
        return None
    j = text.find("\n## ", i + 1)
    return text[i + 1:] if j < 0 else text[i + 1:j]


@check("VNDR-02")
def _(r):
    doc = r / "AGENTS.md" if (r / "AGENTS.md").is_file() else r / "CLAUDE.md"
    return _matches_reference(doc, _PLUGIN_ASSETS / "fleet" / "agents-md-fleet-section.md", _fleet_section)


def _register_file(base, name):
    f = base / name
    return yaml.safe_load(f.read_text()) or {} if f.is_file() else {}


def load_register():
    """(controls by id, checks): the baseline merged with the fleet's overlay
    by id — an overlay record's fields replace the baseline record's, and an
    overlay record with a new id is added. Referential integrity holds on
    the merged result: a check naming an unknown control is a broken row; a
    control no check tests is an objective nothing verifies — the GATE-01
    failure, one level up."""
    base_c = _register_file(BASELINE, "CONTROLS.yaml")
    base_k = _register_file(BASELINE, "CHECKS.yaml")
    over_c = _register_file(REGISTER, "CONTROLS.yaml") if REGISTER else {}
    over_k = _register_file(REGISTER, "CHECKS.yaml") if REGISTER else {}
    ctrl = {c["id"]: dict(c) for c in base_c.get("controls") or []}
    for c in over_c.get("controls") or []:
        ctrl.setdefault(c["id"], {}).update(c)
    by_id = {k["id"]: dict(k) for k in base_k.get("checks") or []}
    for k in over_k.get("checks") or []:
        by_id.setdefault(k["id"], {}).update(k)
    checks = list(by_id.values())
    if not ctrl or not checks:
        sys.exit(f"no register: baseline {BASELINE} holds no controls or checks"
                 + (f" and overlay {REGISTER} adds none" if REGISTER else ""))
    orphans = [k["id"] for k in checks if k.get("control") not in ctrl]
    if orphans:
        sys.exit(f"checks with unknown control: {orphans}")
    untested = [c for c in ctrl if not any(k.get("control") == c for k in checks)]
    if untested:
        sys.exit(f"controls with no checks: {untested}")
    order = {c: i for i, c in enumerate(ctrl)}
    checks.sort(key=lambda k: (order.get(k["control"], 99), k["id"]))
    return ctrl, checks


def family_repos():
    return [n for n in FAMILY if (repo_path(n) / ".git").exists()]


def sev_of(check, ctrl):
    """A check's OWN severity, falling back to its control's.

    Both levels carry one and they disagree for roughly a third of the
    checks — by design: C-GATES is high because a gate that does not run is
    a hole, while GATE-03 under it is cosmetic. The check is the thing being
    reported, so the check's severity is the one that describes the row.

    Reading the control's instead (what this did until 2026-07-25) made
    --fail-on high wrong in both directions at once: it fired on GATE-03,
    CI-14, CTR-04, AUTH-03 and PRE-04 — all declared low or medium — and
    stayed silent on UI-02, SENTRY-03 and SENTRY-04, which declare high
    under a medium control. Over-firing trains people to ignore the gate;
    under-firing is the hole it exists to close. Keep the fallback: a check
    added without a severity must inherit one, never read as unset.
    """
    return check.get("severity") or ctrl[check["control"]]["severity"]


@contextlib.contextmanager
def snapshot_family(ref, repos=()):
    """Audit a detached worktree of `ref` for every family repo and every
    repo in `repos`; the checkout as it sits only when the ref does not
    resolve (a clone with no remote). A worktree that cannot be created is a
    hard error: silently auditing the checkout instead is the drift this
    exists to stop. Family-wide caches live exactly as long as the snapshot."""
    _FLEET.clear()
    snap_root = pathlib.Path(tempfile.mkdtemp(prefix="audit-"))
    try:
        for rn in dict.fromkeys(list(family_repos()) + [x for x in repos if (repo_path(x) / ".git").exists()]):
            REPO_PATH[rn], note = _snapshot(repo_path(rn), ref, snap_root / rn)
            print(f"{rn:<16} {note}", file=sys.stderr)
        print(file=sys.stderr)
        yield
    finally:
        for rn, path in list(REPO_PATH.items()):
            home = REPO_DIR.get(rn, ROOT / rn)
            if path != home:
                rc, _out, err = sh3(home, f"git worktree remove --force {shlex.quote(str(path))}")
                if rc:
                    sh3(home, "git worktree prune")
                    print(f"{rn}: worktree remove failed ({err}); ran `git worktree prune` — "
                          f"check `git -C {home} worktree list`", file=sys.stderr)
        REPO_PATH.clear()
        _FLEET.clear()
        shutil.rmtree(snap_root, ignore_errors=True)


def _snapshot(repo, ref, dest):
    # The worktree's basename must stay the repo name: a dozen checkers
    # dispatch on r.name, and CI-22/PRE-07 key the fleet maps by it.
    rc, sha, _err = sh3(repo, f"git rev-parse --verify -q --short {shlex.quote(ref)}")
    if rc or not sha:
        return repo, f"checkout as-is ({ref} does not resolve)"
    rc, _out, err = sh3(repo, f"git worktree add --detach {shlex.quote(str(dest))} {shlex.quote(ref)}")
    if rc or not (dest / ".git").exists():
        raise RuntimeError(f"{repo.name}: git worktree add failed: {err or f'rc={rc}'}")
    rc, status, _err = sh3(repo, "git status --porcelain --branch")
    lines = status.splitlines() if not rc else []
    branch = lines[0].removeprefix("## ").split("...")[0] if lines else "?"
    dirty = max(len(lines) - 1, 0)
    _rc, lr, _err = sh3(repo, f"git rev-list --left-right --count {shlex.quote(ref)}...HEAD")
    behind, ahead = (lr.split() + ["?", "?"])[:2]
    note = f"{ref} @ {sha}"
    if branch != "main" or dirty or behind != "0" or ahead != "0":
        note += f"  (checkout is on {branch}, {behind} behind / {ahead} ahead, {dirty} dirty)"
    return dest, note


def run_matrix(checks, repos):
    """rows of (check, [(status, detail) per repo]), the FAIL cells, and the
    ERROR cells — a checker that raised. Errors are printed as they happen;
    a broken checker must read as broken, never as PASS or as a by-design
    MANUAL."""
    rows, fails, errors = [], [], []
    for c in checks:
        cells = []
        for rn in repos:
            fn = CHECKS.get(c["id"])
            if not fn:
                cells.append((MANUAL, ""))
                continue
            try:
                st, detail = fn(repo_path(rn))
                if st not in STATUSES:
                    raise ValueError(f"checker returned status {st!r}")
            except Exception as e:
                st, detail = ERROR, f"{type(e).__name__}: {e}"
                print(f"{c['id']} {rn}: {detail}", file=sys.stderr)
                errors.append((c, rn, detail))
            cells.append((st, detail))
            if st == FAIL:
                fails.append((c, rn, detail))
        rows.append((c, cells))
    return rows, fails, errors


MARK = {PASS: "✅", FAIL: "❌", NA: "–", MANUAL: "?", ERROR: "💥"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", action="append")
    ap.add_argument("--control", action="append")
    ap.add_argument("--md", action="store_true", help="markdown table")
    ap.add_argument("--fail-on", default="", help="comma severities that exit non-zero, e.g. high")
    ap.add_argument("--ref", default="origin/main",
                    help="audit this ref of every repo via a detached worktree (default origin/main)")
    ap.add_argument("--no-snapshot", action="store_true",
                    help="audit the checkouts as they sit, whatever branch or dirt they carry")
    ap.add_argument("--fleet", default="", help="the fleet root (default: found by walking up from cwd)")
    ap.add_argument("--json", action="store_true", help="one JSON object per failing (check x repo) cell, for skills")
    a = ap.parse_args()

    configure(a.fleet or None)
    ctrl, checks = load_register()
    if a.control:
        want = set(a.control)
        checks = [k for k in checks if k["id"] in want or k.get("control") in want]
    repos = [x for x in (a.repo or family_repos()) if repo_path(x).is_dir()]
    if not repos:
        sys.exit("no repos to audit: not inside a fleet and not inside a git repo")

    if a.no_snapshot:
        rows, fails, errors = run_matrix(checks, repos)
    else:
        with snapshot_family(a.ref, repos):
            rows, fails, errors = run_matrix(checks, repos)

    w = max(len(r) for r in repos) + 2
    if a.json:
        for c, rn, detail in fails:
            print(json.dumps({"check": c["id"], "control": c["control"], "repo": rn,
                              "severity": sev_of(c, ctrl), "title": c["title"],
                              "reference": c.get("reference") or ctrl[c["control"]].get("reference") or "none",
                              "detail": detail, "rule": " ".join((c.get("rule") or "").split())}))
    elif a.md:
        print("| Control | Check | Sev | " + " | ".join(repos) + " |")
        print("| --- | --- | --- | " + " | ".join("---" for _ in repos) + " |")
        for c, cells in rows:
            print(
                f"| {c.get('control','?')} | **{c['id']}** {c['title']} "
                f"({c.get('scope','?')}) | {sev_of(c, ctrl)[0].upper()} | "
                + " | ".join(
                    MARK[s] + (f" {d}" if s in (FAIL, ERROR) and d else "") for s, d in cells
                )
                + " |"
            )
    else:
        print(f"{'CONTROL':<13}{'CHECK':<12} {'SCOPE':<10}{'SEV':<7}"
              + "".join(f"{r:<{w}}" for r in repos))
        print("-" * (42 + w * len(repos)))
        last = None
        for c, cells in rows:
            cid = c["control"]
            shown = cid if cid != last else ""
            last = cid
            print(
                f"{shown:<13}{c['id']:<12} {c.get('scope',''):<10}"
                f"{sev_of(c, ctrl):<7}"
                + "".join(f"{st:<{w}}" for st, _ in cells)
            )

    hi = [f for f in fails if sev_of(f[0], ctrl) == "high"]
    ctrls_touched = {k["control"] for k in checks}
    failing_ctrls = {f[0]["control"] for f in fails}
    print(f"\n{len(fails)} failing (check x repo) results ({len(hi)} high) "
          f"across {len(repos)} repos" + (f"; {len(errors)} checker errors" if errors else ""))
    print(f"{len(checks)} checks under {len(ctrls_touched)} controls; "
          f"{len(failing_ctrls)} controls have at least one failing check")
    if errors:
        return 2
    if a.fail_on:
        want = set(a.fail_on.split(","))
        if any(sev_of(f[0], ctrl) in want for f in fails):
            return 1
    return 0


# Bind once at import so tests and consistency.py get a usable module; main()
# re-binds when --fleet is given.
configure()

if __name__ == "__main__":
    sys.exit(main())
