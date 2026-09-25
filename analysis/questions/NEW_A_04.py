"""Q2.02 / NEW-A-04 -- Is there a pre-factory period in each repo's history,
before any skills, work-item store or template? (Preflight)
Compares a repo's first commit against the first skill_versions event that
touched THIS repo's own skill history (only wayfare-skills has any -- it IS
the skills history) and its first plan_items row.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import BASELINE_CUTOFF

RQ_ID = "NEW-A-04"
QUESTION = "Is there a pre-factory period in each repo's history, before any skills, work-item store or template?"

SQL = """
SELECT r.repo, r.first_commit_ts,
       (SELECT MIN(created_ts) FROM plans.plan_items i WHERE i.repo = r.repo) AS first_plan_item_ts
FROM git.repos r
ORDER BY r.first_commit_ts
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    return [dict(r, first_commit_before_first_plan_item=(
        r["first_plan_item_ts"] is None or r["first_commit_ts"] < r["first_plan_item_ts"]
    ), first_commit_before_factory_cutoff=r["first_commit_ts"] < BASELINE_CUTOFF) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
