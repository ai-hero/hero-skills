"""Q2.10 / RQ-h1-043 -- Before the factory, what share of commits came from
the human alone versus with an agent co-author?

v_commits.actor (cube/views.sql) already classifies each commit human/agent/
bot from is_bot and claude_trailer; this just splits it by fleet.BASELINE_CUTOFF.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import BASELINE_CUTOFF

RQ_ID = "RQ-h1-043"
QUESTION = "Before the factory, what share of commits came from the human alone versus with an agent co-author?"

SQL = """
SELECT repo, actor, COUNT(*) AS commits
FROM v_commits
WHERE day < ?
GROUP BY repo, actor
ORDER BY repo, actor
"""


def answer(con):
    rows = con.execute(SQL, (BASELINE_CUTOFF,)).fetchall()
    totals = {}
    for r in rows:
        totals.setdefault(r["repo"], 0)
        totals[r["repo"]] += r["commits"]
    return [dict(r, share=round(r["commits"] / totals[r["repo"]], 3)) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
