"""Q6.xx / RQ-h1-028 -- How long does a change made at the design source
take to reach a downstream repo? D3-backed, upstream_repo=fleet.DESIGN_SYSTEM_REPO.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import DESIGN_SYSTEM_REPO

RQ_ID = "RQ-h1-028"
QUESTION = "How long does a change made at the design source take to reach a downstream repo?"

SQL = "SELECT downstream_repo, lag_hours FROM detectors.propagation WHERE upstream_repo = ?"


def answer(con):
    if not DESIGN_SYSTEM_REPO:
        return [{"note": "no design_system_repo configured in .analysis/config.json for this fleet"}]
    rows = con.execute(SQL, (DESIGN_SYSTEM_REPO,)).fetchall()
    if not rows:
        return [{"note": f"no matched arrivals from {DESIGN_SYSTEM_REPO} in the propagation table"}]
    lags = sorted(r["lag_hours"] for r in rows)
    n = len(lags)
    return [{"matched_arrivals": n, "median_lag_hours": lags[n // 2], "max_lag_hours": lags[-1]}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
