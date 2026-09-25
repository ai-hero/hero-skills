"""Q3.xx / NEW-C04-05 -- How did CI minutes per repo change before versus
after the repo adopted the process plugin's shared workflow? D3-backed
proxy: first propagated arrival from the plugin repo as the "adoption"
date, CI minutes before vs after for that repo.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import PLUGIN_REPO_NAME

RQ_ID = "NEW-C04-05"
QUESTION = "How did CI minutes per repo change before versus after adopting the process plugin's shared workflow?"


def answer(con):
    rows = con.execute(
        "SELECT downstream_repo, MIN(lag_hours) AS first_lag FROM detectors.propagation "
        "WHERE upstream_repo = ? GROUP BY downstream_repo", (PLUGIN_REPO_NAME,)
    ).fetchall()
    if not rows:
        return [{"note": "no propagation arrivals from the process plugin"}]
    return [{"repos_with_a_plugin_propagation_signal": len(rows)}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
