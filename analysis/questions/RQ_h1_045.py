"""Q2.08 / RQ-h1-045 -- How did churn per commit and per change set compare
before and after the factory in the same repo? D1-backed.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import BASELINE_CUTOFF

RQ_ID = "RQ-h1-045"
QUESTION = "How did churn per commit and per change set compare before and after the factory?"

SQL = """
SELECT c.repo, CASE WHEN c.day < ? THEN 'before' ELSE 'after' END AS era,
       c.insertions, c.deletions, lk.content_hash
FROM git.commits c
JOIN detectors.changesets_by_commit lk ON lk.repo = c.repo AND lk.sha = c.sha
"""


def answer(con):
    rows = con.execute(SQL, (BASELINE_CUTOFF,)).fetchall()
    hashes = {r["content_hash"] for r in rows}
    n_sets = dict(con.execute(
        f"SELECT content_hash, n_sets FROM detectors.changesets WHERE content_hash IN "
        f"({','.join('?' * len(hashes))})", tuple(hashes)
    ).fetchall()) if hashes else {}

    agg = {}
    for r in rows:
        key = (r["repo"], r["era"])
        a = agg.setdefault(key, {"commits": 0, "churn": 0, "sets": 0})
        churn = (r["insertions"] or 0) + (r["deletions"] or 0)
        a["commits"] += 1
        a["churn"] += churn
        a["sets"] += n_sets.get(r["content_hash"], 1)

    out = []
    for (repo, era), a in sorted(agg.items()):
        out.append({
            "repo": repo, "era": era, "commits": a["commits"],
            "churn_per_commit": round(a["churn"] / a["commits"], 1),
            "churn_per_change_set": round(a["churn"] / a["sets"], 1) if a["sets"] else None,
        })
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
