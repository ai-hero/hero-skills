"""Q4.07 / RQ-h7-011 -- What share of commits are human-only, agent-assisted,
or bot-authored, per repo and over time?

Same v_commits.actor classification as RQ-h1-043, sliced by month instead of
a single before/after split -- this is the full-window trend the baseline
question is a snapshot of.
"""
RQ_ID = "RQ-h7-011"
QUESTION = "What share of commits are human-only, agent-assisted, or bot-authored, per repo and over time?"

SQL = """
SELECT repo, month, actor, COUNT(*) AS commits
FROM v_commits
WHERE month IS NOT NULL
GROUP BY repo, month, actor
ORDER BY repo, month, actor
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    totals = {}
    for r in rows:
        key = (r["repo"], r["month"])
        totals.setdefault(key, 0)
        totals[key] += r["commits"]
    return [dict(r, share=round(r["commits"] / totals[(r["repo"], r["month"])], 3)) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
