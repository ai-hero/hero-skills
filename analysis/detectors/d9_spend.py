"""D9 spend attribution -> .analysis/data/detectors.sqlite, table session_spend.

Session -> branch -> item -> type, reported at the
confidence level the join actually supports:

  - repo/branch: every session has git_branches (a JSON list) and cost_usd,
    a full-confidence split when the session touched exactly one branch,
    weighted evenly across branches when it touched several (a real
    under/over-attribution, not solved here -- see RQ-h1-021's own note
    that multi-branch sessions are the unreliable case).
  - item: only where the branch matches exactly one PR's head_ref
    (github.prs) AND that PR has at least one commit with a parsed
    plan_item_ref in the SAME repo (git.commits.plan_item_ref is a bare
    number with no repo qualifier, so repo-scoping it here is required,
    not optional). Most commits carry no plan_item_ref at all, so
    item-level attribution is low-coverage by construction -- every row
    says so via attribution_confidence, and the branch/repo split above
    does not depend on it.
"""
import json, os, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import OUT

DB_PATH = os.path.join(OUT, "detectors.sqlite")


def build():
    con = sqlite3.connect(DB_PATH)
    con.execute("ATTACH DATABASE ? AS harness", (os.path.join(OUT, "harness.sqlite"),))
    con.execute("ATTACH DATABASE ? AS github", (os.path.join(OUT, "github.sqlite"),))
    con.execute("ATTACH DATABASE ? AS git", (os.path.join(OUT, "git.sqlite"),))

    con.execute("DROP TABLE IF EXISTS session_spend")
    con.execute("""
        CREATE TABLE session_spend (
            session_id_hash TEXT, repo TEXT, branch TEXT, cost_usd REAL,
            branch_count INTEGER, item_id TEXT, attribution_confidence TEXT
        )
    """)

    # repo -> head_ref -> PR numbers with >1 match are ambiguous, skipped for item attribution
    pr_by_branch = {}
    for repo, number, head_ref in con.execute("SELECT repo, number, head_ref FROM github.prs").fetchall():
        pr_by_branch.setdefault((repo, head_ref), []).append(number)

    item_by_repo_pr = {}
    for repo, pr_number, ref in con.execute(
        "SELECT repo, pr_number, plan_item_ref FROM git.commits WHERE pr_number IS NOT NULL AND plan_item_ref IS NOT NULL"
    ).fetchall():
        item_by_repo_pr.setdefault((repo, pr_number), set()).add(ref)

    rows = con.execute("SELECT session_id_hash, repo, git_branches, cost_usd FROM harness.sessions").fetchall()
    out = []
    for session_id, repo, branches_json, cost in rows:
        try:
            branches = json.loads(branches_json) or ["(unknown)"]
        except (json.JSONDecodeError, TypeError):
            branches = ["(unknown)"]
        n = len(branches)
        per_branch_cost = (cost or 0.0) / n
        for branch in branches:
            item_id, confidence = None, "multi_branch" if n > 1 else "branch_no_item"
            if n == 1:
                prs = pr_by_branch.get((repo, branch), [])
                if len(prs) == 1:
                    items = item_by_repo_pr.get((repo, prs[0]))
                    if items and len(items) == 1:
                        item_id = next(iter(items))
                        confidence = "branch_and_item"
            out.append((session_id, repo, branch, per_branch_cost, n, item_id, confidence))

    con.executemany("INSERT INTO session_spend VALUES (?,?,?,?,?,?,?)", out)
    con.commit()

    n_single = sum(1 for r in out if r[4] == 1)
    n_item = sum(1 for r in out if r[6] == "branch_and_item")
    print(f"detectors.sqlite: session_spend {len(out)} rows from {len(rows)} sessions "
          f"({n_single} single-branch rows, {n_item} with an item match)")
    con.close()


if __name__ == "__main__":
    build()
