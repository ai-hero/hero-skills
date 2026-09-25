"""Q11.xx / RQ-h3-027 -- When a hardening fix lands in one clone, how many
sibling clones still carry the gap? Same D7/D3 cluster data as RQ-h6-002,
scoped to security-shaped commits (subject mentions vulnerab/CVE/security/
harden), counting the clones a sweep DIDN'T reach.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import GROUPS

RQ_ID = "RQ-h3-027"
QUESTION = "When a hardening fix lands in one clone, how many sibling clones still carry the gap?"


def answer(con):
    clones = {r for r, g in GROUPS.items() if g == "apps"}
    rows = con.execute(
        "SELECT df.cluster_id, GROUP_CONCAT(DISTINCT df.repo) AS repos FROM detectors.duplicate_fixes df "
        "JOIN git.commits c ON c.repo = df.repo AND c.sha = df.sha "
        "WHERE c.subject LIKE '%vulnerab%' OR c.subject LIKE '%CVE%' OR c.subject LIKE '%harden%' "
        "OR c.subject LIKE '%security%' GROUP BY df.cluster_id"
    ).fetchall()
    out = []
    for r in rows:
        reached = set(r["repos"].split(",")) & clones
        out.append({"cluster_id": r["cluster_id"], "clones_reached": len(reached),
                    "clones_still_missing": len(clones - reached)})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
