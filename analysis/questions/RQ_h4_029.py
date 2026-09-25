"""Q13.xx / RQ-h4-029 -- How long does a surface released in a design
source take to reach the product, per downstream repo? Same D3 source as
RQ-h1-028, broken out per repo instead of fleet-wide.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import DESIGN_SYSTEM_REPO

RQ_ID = "RQ-h4-029"
QUESTION = "How long does a surface released in a design source take to reach the product, per downstream repo?"

SQL = "SELECT downstream_repo, lag_hours FROM detectors.propagation WHERE upstream_repo = ?"


def answer(con):
    if not DESIGN_SYSTEM_REPO:
        return [{"note": "no design_system_repo configured in .analysis/config.json for this fleet"}]
    rows = con.execute(SQL, (DESIGN_SYSTEM_REPO,)).fetchall()
    by_repo = {}
    for r in rows:
        by_repo.setdefault(r["downstream_repo"], []).append(r["lag_hours"])
    if not by_repo:
        return [{"note": f"no matched arrivals from {DESIGN_SYSTEM_REPO} in the propagation table"}]
    return [{"repo": repo, "arrivals": len(lags), "median_lag_hours": sorted(lags)[len(lags) // 2]}
            for repo, lags in by_repo.items()]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
