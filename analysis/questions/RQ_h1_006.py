"""Q12.xx / RQ-h1-006 -- As the shared design system's registry grows,
does its code grow in proportion, or does one part (tests, unused surface)
outpace shipped output? registry.json (the actual item count) isn't
ingested by anything here -- only code volume is available (commit_files),
so the registry-count half of the comparison can't be made.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import DESIGN_SYSTEM_REPO

RQ_ID = "RQ-h1-006"
QUESTION = "As the shared design system's registry grows, does its code grow in proportion?"


def answer(con):
    if not DESIGN_SYSTEM_REPO:
        return [{"note": "no design_system_repo configured in .analysis/config.json for this fleet"}]
    rows = con.execute(
        "SELECT month, SUM(insertions) - SUM(deletions) AS net_lines "
        "FROM git.commits WHERE repo = ? AND month IS NOT NULL GROUP BY month ORDER BY month",
        (DESIGN_SYSTEM_REPO,),
    ).fetchall()
    return [{"answerable_by_code": "partial", "reason": "registry.json item count isn't ingested, "
             "only code volume is -- reported alone, not as a ratio"}] + [dict(r) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
