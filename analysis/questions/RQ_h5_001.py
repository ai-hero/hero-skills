"""Q14.xx / RQ-h5-001 -- What share of each clone's work items are
compliance, security or upkeep rather than product feature work?
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import GROUPS

RQ_ID = "RQ-h5-001"
QUESTION = "What share of each clone's work items are compliance/security/upkeep rather than product feature work?"

UPKEEP_TYPES = ("chore", "security", "docs")


def answer(con):
    clones = [r for r, g in GROUPS.items() if g == "apps"]
    if not clones:
        return [{"note": "no repos with FLEET.md group=apps found"}]
    q = f"""
        SELECT repo, type, COUNT(*) AS n FROM plans.plan_items
        WHERE type != 'goal' AND repo IN ({','.join('?' * len(clones))})
        GROUP BY repo, type
    """
    rows = con.execute(q, clones).fetchall()
    by_repo = {}
    for r in rows:
        b = by_repo.setdefault(r["repo"], {"upkeep": 0, "other": 0})
        b["upkeep" if r["type"] in UPKEEP_TYPES else "other"] += r["n"]
    return [{"repo": repo, **v, "upkeep_share": round(v["upkeep"] / (v["upkeep"] + v["other"]), 3)}
            for repo, v in sorted(by_repo.items())]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
