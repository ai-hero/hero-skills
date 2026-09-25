"""Q12.xx / NEW-A-09 -- How homogeneous is the fleet: how many repos share
the template's stack? Proxy: repos sharing the template's presence
fingerprint (same set of D10 artifacts present at HEAD).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import TEMPLATE_REPO

RQ_ID = "NEW-A-09"
QUESTION = "How homogeneous is the fleet: how many repos share the template's stack fingerprint?"


def answer(con):
    if not TEMPLATE_REPO:
        return [{"note": "no FLEET.md group: template repo in this fleet"}]
    rows = con.execute(
        "SELECT repo, artifact, present FROM detectors.presence WHERE snapshot = 'head'"
    ).fetchall()
    fingerprints = {}
    for r in rows:
        fingerprints.setdefault(r["repo"], {})[r["artifact"]] = r["present"]

    template_fp = fingerprints.get(TEMPLATE_REPO)
    if not template_fp:
        return [{"note": f"no presence fingerprint found for {TEMPLATE_REPO}"}]
    matches = sum(1 for repo, fp in fingerprints.items() if repo != TEMPLATE_REPO and fp == template_fp)
    return [{"repos_checked": len(fingerprints) - 1, "repos_matching_template_fingerprint": matches,
             "template_fingerprint": template_fp}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
