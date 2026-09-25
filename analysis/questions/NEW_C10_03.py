"""Q10.xx / NEW-C10-03 -- How often does a skill change cause a regression
in a downstream repo? D3+D5-backed: a process-plugin commit that propagated
downstream (D3), where the downstream arrival commit itself got a D5
follow-up within 14 days, is the candidate signal for "caused a regression
that needed a fix" -- a follow-up could also just be unrelated later work
on the same files, so this is an upper bound, not a confirmed regression
count (confirming would need reading each pair's actual diffs).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import PLUGIN_REPO_NAME

RQ_ID = "NEW-C10-03"
QUESTION = "How often does a skill change cause a regression in a downstream repo?"

SQL = """
SELECT p.upstream_sha, p.downstream_repo, p.downstream_sha, p.lag_hours,
       c.pr_number
FROM detectors.propagation p
LEFT JOIN git.commits c ON c.repo = p.downstream_repo AND c.sha = p.downstream_sha
WHERE p.upstream_repo = ?
"""


def answer(con):
    rows = con.execute(SQL, (PLUGIN_REPO_NAME,)).fetchall()
    with_followup = 0
    out = []
    for r in rows:
        followed_up = False
        if r["pr_number"] is not None:
            f = con.execute(
                "SELECT followup_within_14d_days FROM detectors.followups WHERE repo = ? AND number = ?",
                (r["downstream_repo"], r["pr_number"]),
            ).fetchone()
            followed_up = bool(f and f[0] is not None)
        with_followup += followed_up
        out.append({**dict(r), "candidate_regression": followed_up})
    return [{"summary": f"{len(rows)} skill-change arrivals downstream, "
                         f"{with_followup} followed by a same-file fix within 14 days (upper bound, not confirmed)"}] + out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
