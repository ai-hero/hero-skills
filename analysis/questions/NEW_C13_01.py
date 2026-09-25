"""Q13.xx / NEW-C13-01 -- Does every repo record its plans, decisions and
agent memory in files the factory can read? D10-backed (.plans dir,
DESIGN.md presence) + harness.memories repo coverage.
"""
RQ_ID = "NEW-C13-01"
QUESTION = "Does every repo record its plans, decisions and agent memory in files the factory can read?"

SQL = """
SELECT p.repo,
       MAX(CASE WHEN p.artifact = 'plans_dir' THEN p.present END) AS has_plans_dir,
       MAX(CASE WHEN p.artifact = 'design_md' THEN p.present END) AS has_design_md
FROM detectors.presence p
WHERE p.snapshot = 'head'
GROUP BY p.repo
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    memory_repos = {r[0] for r in con.execute("SELECT DISTINCT repo FROM harness.memories").fetchall()}
    return [dict(r, has_recorded_memory=r["repo"] in memory_repos) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
