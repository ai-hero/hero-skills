"""Q12.xx / RQ-h1-016 -- What share of each repo's work items are features
versus structural work (chores, bugs, security, etc), and does that split
differ between repos judged to be building a product and repos doing
upkeep only?

The plan_items.type column is already normalized across both schema eras by
ingest/plans.py (feature/chore/bug/goal/security/feedback/research/polish/
docs/unknown) -- no frontmatter parsing needed here.

fleet.NO_ROADMAP_YET (config `no_roadmap_yet`) repos
have no stated feature roadmap yet, so their near-zero feature share isn't
evidence of "upkeep-only" the way it would be for a mature repo -- it's
just early. Flagged, not excluded, so the caller can decide.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import NO_ROADMAP_YET

RQ_ID = "RQ-h1-016"
QUESTION = "What share of each repo's work items are features vs structural work?"

SQL = """
SELECT repo,
       COUNT(*) AS items,
       SUM(CASE WHEN type = 'feature' THEN 1 ELSE 0 END) AS feature_items,
       ROUND(SUM(CASE WHEN type = 'feature' THEN 1 ELSE 0 END) * 1.0 / COUNT(*), 3) AS feature_share
FROM plans.plan_items
WHERE type != 'goal'
GROUP BY repo
ORDER BY feature_share DESC
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    return [dict(r, no_roadmap_yet=r["repo"] in NO_ROADMAP_YET) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
