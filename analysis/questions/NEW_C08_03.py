"""Q14.xx / NEW-C08-03 -- Is there a control register every repo in the
fleet is checked against? knowledge.check_results repo coverage against
the full fleet.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import FLEET_REPOS

RQ_ID = "NEW-C08-03"
QUESTION = "Is there a control register every repo in the fleet is checked against?"


def answer(con):
    checked = {r[0] for r in con.execute("SELECT DISTINCT repo FROM knowledge.check_results").fetchall()}
    missing = [r for r in FLEET_REPOS if r not in checked]
    return [{"fleet_repos": len(FLEET_REPOS), "repos_with_check_results": len(checked),
             "fleet_repos_never_checked": missing}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
