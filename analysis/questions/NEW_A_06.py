"""Q2.16 / NEW-A-06 -- Before the factory, were changes reviewed, and by
whom: a human, an automated reviewer, or nobody?

Baseline: measures the manual, pre-factory period (fleet.BASELINE_CUTOFF).
A PR "reviewed" here means it has at least one row in pr_reviews; "by whom"
splits on reviewer_is_bot (set by github.py's login-shape heuristic, e.g.
github-actions, copilot-pull-request-reviewer[bot]).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import BASELINE_CUTOFF

RQ_ID = "NEW-A-06"
QUESTION = "Before the factory, were changes reviewed, and by whom?"

SQL = """
SELECT p.repo,
       COUNT(*) AS pre_factory_prs,
       SUM(CASE WHEN r.human_reviews > 0 THEN 1 ELSE 0 END) AS human_reviewed,
       SUM(CASE WHEN r.bot_reviews > 0 THEN 1 ELSE 0 END) AS bot_reviewed,
       SUM(CASE WHEN COALESCE(r.human_reviews, 0) = 0 AND COALESCE(r.bot_reviews, 0) = 0 THEN 1 ELSE 0 END) AS unreviewed
FROM github.prs p
LEFT JOIN (
    SELECT repo, number,
           SUM(CASE WHEN reviewer_is_bot = 0 THEN 1 ELSE 0 END) AS human_reviews,
           SUM(CASE WHEN reviewer_is_bot = 1 THEN 1 ELSE 0 END) AS bot_reviews
    FROM github.pr_reviews GROUP BY repo, number
) r ON r.repo = p.repo AND r.number = p.number
WHERE p.day < ?
GROUP BY p.repo
HAVING COUNT(*) > 0
ORDER BY pre_factory_prs DESC
"""


def answer(con):
    return con.execute(SQL, (BASELINE_CUTOFF,)).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
