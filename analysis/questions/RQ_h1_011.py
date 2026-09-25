"""Q12.xx / RQ-h1-011 -- How completely does the fleet map account for the
repos actually checked out? Compares FLEET.md's declared repos (ingest/
fleet.py's own parse) against every directory actually present under
the fleet root.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import ROOT, GROUPS

RQ_ID = "RQ-h1-011"
QUESTION = "How completely does the fleet map account for the repos actually checked out?"


def answer(con=None):
    on_disk = {d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d, ".git"))}
    mapped = set(GROUPS.keys())
    return [{
        "repos_on_disk": len(on_disk), "repos_in_fleet_md": len(mapped),
        "on_disk_but_unmapped": sorted(on_disk - mapped),
        "mapped_but_missing_on_disk": sorted(mapped - on_disk),
    }]


if __name__ == "__main__":
    for row in answer():
        print(row)
