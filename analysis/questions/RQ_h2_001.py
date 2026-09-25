"""Q16.xx / RQ-h2-001 -- How are CI minutes distributed across the template
repo, the clones and the infrastructure repos?

ci_jobs.billable_ms is 0 while runs are inside GitHub Actions' free tier,
so wall-clock run duration (ci_runs.duration_s) is the cost proxy.
billable_minutes is still reported so a run outside the free tier shows up.
"""
RQ_ID = "RQ-h2-001"
QUESTION = "How are CI minutes distributed across the template, the clones and infra?"

SQL = """
SELECT r.role,
       COUNT(DISTINCT c.repo || ':' || c.run_id) AS runs,
       ROUND(SUM(c.duration_s) / 60.0, 1) AS run_minutes,
       ROUND(SUM(COALESCE(j.billable_ms, 0)) / 60000.0, 1) AS billable_minutes,
       COUNT(j.run_id) AS runs_with_billable_data
FROM github.ci_runs c
JOIN git.repos r ON r.repo = c.repo
LEFT JOIN github.ci_jobs j ON j.repo = c.repo AND j.run_id = c.run_id
GROUP BY r.role
ORDER BY run_minutes DESC
"""


def answer(con):
    return con.execute(SQL).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
