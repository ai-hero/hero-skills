"""Q3.11 / RQ-h6-044 -- Does the model or harness version used for a piece
of work correlate with follow-up fixes, throughput or turn duration?
Model half is RQ-h6-046 (commit trailer_model vs D5 follow-up rate). This
covers the harness-version half: sessions.cc_version against the session's
own interrupted_count share, since D9's item linkage is too sparse to
reach follow-up fixes from cc_version reliably.
"""
RQ_ID = "RQ-h6-044"
QUESTION = "Does the harness (Claude Code) version used correlate with interrupted sessions?"

SQL = """
SELECT cc_version, COUNT(*) AS sessions,
       SUM(CASE WHEN interrupted_count > 0 THEN 1 ELSE 0 END) AS interrupted,
       ROUND(AVG(cost_usd), 2) AS avg_cost_usd
FROM harness.sessions
WHERE cc_version IS NOT NULL
GROUP BY cc_version
HAVING sessions >= 5
ORDER BY sessions DESC
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    return [dict(r, interrupted_share=round(r["interrupted"] / r["sessions"], 3)) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
