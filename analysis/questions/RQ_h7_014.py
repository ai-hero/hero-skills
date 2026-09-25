"""Q4.xx / RQ-h7-014 -- How often does the owner deny a tool call or clear
an agent's context, and is that changing?

tool_calls.was_rejected is set at ingest time from the transcript's own
permission-decision record. "Clear an agent's context" (a /clear or fresh
session start) isn't a tool call, so it isn't in this table yet -- this
answers only the denial half; session-restart rate would need a separate
query over sessions.first_ts gaps, not implemented here.
"""
RQ_ID = "RQ-h7-014"
QUESTION = "How often does the owner deny a tool call, and is that changing?"

SQL = """
SELECT strftime('%Y-%m', ts) AS month,
       COUNT(*) AS tool_calls,
       SUM(was_rejected) AS denied,
       ROUND(SUM(was_rejected) * 1.0 / COUNT(*), 4) AS denial_rate
FROM harness.tool_calls
WHERE ts IS NOT NULL
GROUP BY month
ORDER BY month
"""


def answer(con):
    return con.execute(SQL).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
