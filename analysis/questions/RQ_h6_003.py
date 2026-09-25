"""Q10.xx / RQ-h6-003 -- How long does a fix made in the template or process
plugin take to reach each clone? D3-backed, filtered to those two upstreams.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import TEMPLATE_REPO, PLUGIN_REPO_NAME

RQ_ID = "RQ-h6-003"
QUESTION = "How long does a fix made in the template or process plugin take to reach each clone?"

SQL = """
SELECT upstream_repo, downstream_repo, match_method, lag_hours
FROM detectors.propagation
WHERE upstream_repo IN ({placeholders})
ORDER BY upstream_repo, lag_hours
"""


def answer(con):
    upstreams = [r for r in (TEMPLATE_REPO, PLUGIN_REPO_NAME) if r]
    if not upstreams:
        return [{"note": "no template or process plugin repo identified for this fleet"}]
    sql = SQL.format(placeholders=",".join("?" * len(upstreams)))
    rows = con.execute(sql, upstreams).fetchall()
    by_upstream = {}
    for r in rows:
        by_upstream.setdefault(r["upstream_repo"], []).append(r["lag_hours"])
    summary = [{"upstream_repo": u, "n_matched_arrivals": len(v),
                "median_lag_hours": sorted(v)[len(v) // 2], "max_lag_hours": max(v)}
               for u, v in by_upstream.items()]
    return summary + [dict(r) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
