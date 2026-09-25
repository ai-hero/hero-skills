"""D10 presence scanner -> .analysis/data/detectors.sqlite, table presence.

"Does X exist, per repo, over time." Snapshots are the commits already in
git.sqlite (first commit, last commit of each month, and the newest ingested
commit as HEAD) -- no new git log walk, no fetch. Existence is read with
`git cat-file -e <sha>:<path>`, which touches the object database only and
never checks out or writes anything. Local only: no GitHub call, so this
detector carries no rate-limit risk.

Most yes/no and inventory questions in the bank (Q2.xx, chapter preflights,
"does the register have X") are a lookup against this one table.
"""
import os, sqlite3, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import ALL_REPOS, path_of, role_of, OUT

DB_PATH = os.path.join(OUT, "detectors.sqlite")
GIT_DB_PATH = os.path.join(OUT, "git.sqlite")

# name -> path at repo root. "workflows" is a directory, checked with
# ls-tree instead of cat-file -e.
ARTIFACTS = {
    "gitignore": (".gitignore", "file"),
    "env_example": (".env.example", "file"),
    "pre_commit_config": (".pre-commit-config.yaml", "file"),
    "github_workflows": (".github/workflows", "dir"),
    "design_md": ("DESIGN.md", "file"),
    "hero_md": ("HERO.md", "file"),
    "agents_md": ("AGENTS.md", "file"),
    "claude_md": ("CLAUDE.md", "file"),
    "fleet_md": ("FLEET.md", "file"),
}

# .plans is untracked local state (excluded via .git/info/exclude, per
# ingest/plans.py's own docstring), so `git cat-file`/`ls-tree` can NEVER
# see it -- checked via a live filesystem stat instead, and only for
# "head" (there is no way to know a historical snapshot's untracked state).
LIVE_ONLY_ARTIFACTS = {"plans_dir": ".plans"}


def run_git(path, args, check=True):
    return subprocess.run(
        ["git", "-C", path] + args,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        encoding="utf-8", errors="replace", check=check,
    )


def exists_at(path, sha, artifact_path, kind):
    if kind == "file":
        return run_git(path, ["cat-file", "-e", f"{sha}:{artifact_path}"], check=False).returncode == 0
    p = run_git(path, ["ls-tree", "--name-only", sha, "--", artifact_path], check=False)
    return p.returncode == 0 and p.stdout.strip() != ""


def snapshots_for(gcon, repo):
    """(label, sha, ts): first commit, last commit of each month, and the
    newest ingested commit (our HEAD, which may lag true HEAD by however
    stale git.sqlite is -- callers needing true HEAD should re-run ingest/git.py first)."""
    rows = gcon.execute(
        "SELECT sha, committed_ts, month FROM commits WHERE repo = ? ORDER BY committed_ts", (repo,)
    ).fetchall()
    if not rows:
        return []
    out = [("first_commit", rows[0][0], rows[0][1])]
    last_in_month = {}
    for sha, ts, month in rows:
        last_in_month[month] = (sha, ts)  # rows are ordered, so this ends up the last one per month
    for month, (sha, ts) in sorted(last_in_month.items()):
        out.append((f"month_end:{month}", sha, ts))
    out.append(("head", rows[-1][0], rows[-1][1]))
    return out


def build():
    if not os.path.exists(GIT_DB_PATH):
        sys.exit("detectors/d10_presence.py needs .analysis/data/git.sqlite -- run ingest/git.py first")

    gcon = sqlite3.connect(GIT_DB_PATH)

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("DROP TABLE IF EXISTS presence")
    con.execute("""
        CREATE TABLE presence (
            repo TEXT, role TEXT, snapshot TEXT, sha TEXT, ts TEXT, month TEXT,
            artifact TEXT, present INTEGER,
            PRIMARY KEY (repo, snapshot, artifact)
        )
    """)

    n_repos, n_rows = 0, 0
    for repo in ALL_REPOS:
        path = path_of(repo)
        if not os.path.isdir(path):
            continue
        snaps = snapshots_for(gcon, repo)
        if not snaps:
            continue
        n_repos += 1
        role = role_of(repo)
        rows = []
        for label, sha, ts in snaps:
            month = ts[:7] if ts else None
            for artifact, (artifact_path, kind) in ARTIFACTS.items():
                present = 1 if exists_at(path, sha, artifact_path, kind) else 0
                rows.append((repo, role, label, sha, ts, month, artifact, present))
            if label == "head":
                for artifact, rel_path in LIVE_ONLY_ARTIFACTS.items():
                    present = 1 if os.path.isdir(os.path.join(path, rel_path)) else 0
                    rows.append((repo, role, label, sha, ts, month, artifact, present))
        con.executemany(
            "INSERT INTO presence VALUES (?,?,?,?,?,?,?,?)", rows
        )
        n_rows += len(rows)
        con.commit()
        print(f"  {repo}: {len(snaps)} snapshots x {len(ARTIFACTS)} artifacts", file=sys.stderr)

    con.execute("CREATE TABLE IF NOT EXISTS meta (source TEXT, path TEXT, rows INTEGER, extracted_at TEXT)")
    import datetime as dt
    con.execute("DELETE FROM meta WHERE source = 'presence'")
    con.execute("INSERT INTO meta VALUES (?,?,?,?)",
                ("presence", GIT_DB_PATH, n_rows, dt.datetime.now(dt.timezone.utc).isoformat()))
    con.commit()
    con.close()
    gcon.close()
    print(f"detectors.sqlite: presence {n_rows} rows across {n_repos} repos")


if __name__ == "__main__":
    build()
