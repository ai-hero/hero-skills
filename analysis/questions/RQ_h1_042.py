"""Q2.09 / RQ-h1-042 -- How many commits per day did each repo see before the factory?

Baseline only (status: baseline in bank/questions.csv): this measures the
manual, pre-factory period, not a target. See fleet.BASELINE_CUTOFF for the
cutoff date and its caveat.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import BASELINE_CUTOFF

RQ_ID = "RQ-h1-042"
QUESTION = "How many commits per day did each repo see before the factory?"

SQL = """
SELECT repo,
       COUNT(*) AS pre_factory_commits,
       MIN(day) AS first_day,
       MAX(day) AS last_pre_factory_day,
       CAST(julianday(MAX(day)) - julianday(MIN(day)) + 1 AS INTEGER) AS span_days,
       ROUND(COUNT(*) * 1.0 / MAX(1, julianday(MAX(day)) - julianday(MIN(day)) + 1), 3) AS commits_per_day
FROM v_commits
WHERE day < ?
GROUP BY repo
HAVING COUNT(*) > 0
ORDER BY commits_per_day DESC
"""


def answer(con):
    return con.execute(SQL, (BASELINE_CUTOFF,)).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
