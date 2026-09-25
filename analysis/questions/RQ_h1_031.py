"""Q9.xx / RQ-h1-031 -- How many change sets does the factory merge per day
and per week, per repo and fleet-wide?

"Change sets" here means commits (the detector-refined change-set count
from D1 is used where a question needs the split-out count specifically;
this is the coarser, always-available commit-level cadence).
"""
RQ_ID = "RQ-h1-031"
QUESTION = "How many change sets does the factory merge per day and per week, per repo and fleet-wide?"

SQL = """
SELECT repo, week, COUNT(*) AS commits
FROM v_commits
WHERE week IS NOT NULL
GROUP BY repo, week
ORDER BY repo, week
"""

FLEET_SQL = """
SELECT week, COUNT(*) AS commits
FROM v_commits
WHERE week IS NOT NULL
GROUP BY week
ORDER BY week
"""


def answer(con):
    per_repo = [dict(r) for r in con.execute(SQL).fetchall()]
    fleet = [dict(r, repo="(fleet)") for r in con.execute(FLEET_SQL).fetchall()]
    return per_repo + fleet


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
