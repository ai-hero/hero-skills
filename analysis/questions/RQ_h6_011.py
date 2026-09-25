"""Q10.xx / RQ-h6-011 -- How often is the human 'go' gate exercised for
each goal, and does granting many at once change anything?
Proxy: wayfare-start-goal skill invocations (each is a 'go') per week,
grouped to see same-day batches -- same "one sitting" idea as RQ-h7-002,
applied to goal starts instead of item ready-marks.
"""
RQ_ID = "RQ-h6-011"
QUESTION = "How often is the human 'go' gate exercised for each goal, and does granting many at once change anything?"

SQL = """
SELECT substr(t.ts, 1, 10) AS day, COUNT(*) AS goals_started
FROM harness.tool_calls t
WHERE t.skill_name LIKE '%wayfare-start-goal%'
GROUP BY day
ORDER BY goals_started DESC
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    multi_goal_days = sum(1 for r in rows if r["goals_started"] > 1)
    return [{"days_with_a_goal_start": len(rows), "days_with_more_than_one": multi_goal_days}] + [dict(r) for r in rows[:15]]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
