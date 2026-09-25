"""Q10.xx / RQ-h6-007 -- In each clone, what share of work goes through the
small-task runner versus the goal-driven pipeline?
Proxy: skill invocation counts, wayfare-build-task/wayfare-run-task
(small-task runner, both naming eras) vs wayfare-start-goal (goal-driven),
joined to the session's repo.
"""
RQ_ID = "RQ-h6-007"
QUESTION = "In each clone, what share of work goes through the small-task runner versus the goal-driven pipeline?"

SQL = """
SELECT s.repo,
       SUM(CASE WHEN t.skill_name LIKE '%wayfare-run-task%' OR t.skill_name LIKE '%wayfare-build-task%' THEN 1 ELSE 0 END) AS small_task_runner,
       SUM(CASE WHEN t.skill_name LIKE '%wayfare-start-goal%' THEN 1 ELSE 0 END) AS goal_driven
FROM harness.tool_calls t
JOIN harness.sessions s ON s.session_id_hash = t.session_id_hash
WHERE t.skill_name IS NOT NULL
GROUP BY s.repo
HAVING small_task_runner + goal_driven > 0
ORDER BY small_task_runner + goal_driven DESC
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    out = []
    for r in rows:
        total = r["small_task_runner"] + r["goal_driven"]
        out.append(dict(r, small_task_share=round(r["small_task_runner"] / total, 3)))
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
