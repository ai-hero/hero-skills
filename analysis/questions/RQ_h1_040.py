"""Q9.xx / RQ-h1-040 -- Before the factory, what was a repo's change wall
time, merge cadence and change-set size? D1-backed, filtered to
fleet.BASELINE_CUTOFF, reusing NEW-A-05's pattern for the pre-factory window.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import BASELINE_CUTOFF

RQ_ID = "RQ-h1-040"
QUESTION = "Before the factory, what was a repo's change wall time, merge cadence and change-set size?"


def answer(con):
    prs = con.execute("SELECT repo, hours_to_merge FROM github.prs WHERE day < ? AND hours_to_merge IS NOT NULL",
                       (BASELINE_CUTOFF,)).fetchall()
    by_repo = {}
    for r in prs:
        by_repo.setdefault(r["repo"], []).append(r["hours_to_merge"])
    out = []
    for repo, hours in sorted(by_repo.items()):
        hours.sort()
        n = len(hours)
        out.append({"repo": repo, "pre_factory_merged_prs": n, "median_hours_to_merge": round(hours[n // 2], 1)})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
