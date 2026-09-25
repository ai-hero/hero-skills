"""Q12.xx / NEW-A-08 -- Does the factory keep a fleet map naming every repo
and its role? FLEET.md lives at the fleet root, not per-repo, so this is a
straight filesystem check plus the role vocabulary git.repos already has.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import ROOT, FLEET_REPOS

RQ_ID = "NEW-A-08"
QUESTION = "Does the factory keep a fleet map naming every repo and its role?"


def answer(con):
    fleet_md = os.path.join(ROOT, "FLEET.md")
    roles = con.execute("SELECT repo, role FROM git.repos").fetchall()
    return [{
        "fleet_md_exists": os.path.exists(fleet_md),
        "fleet_md_path": fleet_md,
        "repos_in_fleet_md_group": len(FLEET_REPOS),
        "repos_with_a_role_in_git_repos": len(roles),
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
