"""D8 gate firings -> detectors.sqlite, table gate_firings.

A CI "catch" = the same (repo, workflow_name, head_sha) has a failure run
followed by a success run -- reuses the exact grouping RQ_cicd_003.py
already validated, so a catch here and a "flake" there are the same
underlying event read two ways: RQ_cicd_003 asks whether the failure meant
anything (yes, if only the flaky workflows dominate it); this asks how
often each gate fires at all, flaky or not. Review verdicts come straight
from pr_reviews.state. No pre-commit/pre-push signal -- that needs local
hook logs this fleet doesn't retain, so "a gate never seen failing" here
means "never seen failing in CI or review," not "never fires."
"""
import os, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import OUT

DB_PATH = os.path.join(OUT, "detectors.sqlite")
GITHUB_DB = os.path.join(OUT, "github.sqlite")


def build():
    con = sqlite3.connect(DB_PATH)
    con.execute("ATTACH DATABASE ? AS github", (GITHUB_DB,))

    rows = con.execute(
        "SELECT repo, workflow_name, head_sha, conclusion, created_ts FROM github.ci_runs "
        "WHERE conclusion IN ('failure', 'success') ORDER BY repo, workflow_name, head_sha, created_ts"
    ).fetchall()
    groups = {}
    for repo, wf, sha, concl, ts in rows:
        groups.setdefault((repo, wf, sha), []).append((concl, ts))

    ci_catches = []
    for (repo, wf, sha), seq in groups.items():
        for i, (concl, ts) in enumerate(seq):
            if concl == "failure" and any(c == "success" for c, _ in seq[i + 1:]):
                ci_catches.append((repo, wf, sha, ts))

    con.execute("DROP TABLE IF EXISTS gate_firings")
    con.execute("""
        CREATE TABLE gate_firings (
            gate_kind TEXT, repo TEXT, ref TEXT, actor TEXT, verdict TEXT, ts TEXT
        )
    """)
    rows_out = [("ci", repo, wf, None, "caught", ts) for repo, wf, sha, ts in ci_catches]

    for repo, number, reviewer, is_bot, state, ts in con.execute(
        "SELECT repo, number, reviewer, reviewer_is_bot, state, submitted_ts FROM github.pr_reviews"
    ).fetchall():
        actor = "bot" if is_bot else "human"
        rows_out.append(("review", repo, str(number), actor, state, ts))

    con.executemany("INSERT INTO gate_firings VALUES (?,?,?,?,?,?)", rows_out)
    con.commit()

    n_ci = sum(1 for r in rows_out if r[0] == "ci")
    n_changes_requested = sum(1 for r in rows_out if r[0] == "review" and r[4] == "CHANGES_REQUESTED")
    print(f"detectors.sqlite: gate_firings {len(rows_out)} rows "
          f"({n_ci} CI catches, {n_changes_requested} review CHANGES_REQUESTED verdicts)")
    con.close()


if __name__ == "__main__":
    build()
