"""Q16.xx / RQ-h2-003 -- What is the spend and CI time per shipped change
set in each clone, and does a new clone's ratio settle as it matures?
Same per-repo rate as RQ-h2-020, scoped to clones, plus CI minutes.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import GROUPS

RQ_ID = "RQ-h2-003"
QUESTION = "What is the spend and CI time per shipped change set in each clone?"


def answer(con):
    from questions.RQ_h2_020 import answer as spend_answer
    spend_rows = {r["repo"]: r for r in spend_answer(con)}
    ci = {r["repo"]: r["minutes"] for r in con.execute(
        "SELECT repo, SUM(duration_s) / 60.0 AS minutes FROM github.ci_runs GROUP BY repo"
    ).fetchall()}
    clones = [r for r, g in GROUPS.items() if g == "apps"]
    out = []
    for repo in clones:
        if repo in spend_rows:
            out.append({**spend_rows[repo], "ci_minutes": round(ci.get(repo, 0), 1)})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
