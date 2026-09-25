"""Q4.xx / RQ-h7-008 -- How often, and why, does the owner stop a running
agent mid-task, and does the rate vary week to week?

sessions.interrupted_count is set at ingest from the transcript's own
interrupt markers. "Why" isn't captured as a structured field -- prompts
text after an interrupt would need a Haiku pass to classify, not done here.
"""
RQ_ID = "RQ-h7-008"
QUESTION = "How often does the owner stop a running agent mid-task, and does the rate vary week to week?"

SQL = """
SELECT week,
       COUNT(*) AS sessions,
       SUM(interrupted_count) AS interrupts,
       SUM(CASE WHEN interrupted_count > 0 THEN 1 ELSE 0 END) AS sessions_with_interrupt,
       ROUND(SUM(CASE WHEN interrupted_count > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*), 3) AS interrupted_session_share
FROM harness.sessions
WHERE week IS NOT NULL
GROUP BY week
ORDER BY week
"""


def answer(con):
    return con.execute(SQL).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
