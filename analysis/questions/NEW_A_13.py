"""Q12.xx / NEW-A-13 -- Is the fleet's architecture described in a central
repo, in each repo, or both? D10-backed: fleet_md presence (central, at the
fleet root, not per-repo) + design_md presence per repo (local).
"""
RQ_ID = "NEW-A-13"
QUESTION = "Is the fleet's architecture described in a central repo, in each repo, or both?"


def answer(con):
    per_repo = con.execute(
        "SELECT repo, present FROM detectors.presence WHERE snapshot='head' AND artifact='design_md'"
    ).fetchall()
    n_with = sum(1 for r in per_repo if r["present"])
    return [{
        "central_fleet_level_doc": "FLEET.md + .fleet/ register (fleet root, not any one repo)",
        "repos_with_own_design_md": n_with, "repos_checked": len(per_repo),
        "answer": "both -- a central fleet map/register plus a per-repo DESIGN.md",
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
