"""Q13.xx / NEW-C13-02 -- Does each repo expose a fixed set of observable
signals (health, logs, CI status)?
Proxy: has a .github/workflows dir at all (D10), and whether any of its CI
runs come from a workflow whose name mentions health/deploy/scan (a coarse
keyword match on workflow_name, not a check of what each workflow verifies).
"""
RQ_ID = "NEW-C13-02"
QUESTION = "Does each repo expose a fixed set of observable signals (health, logs, CI status)?"

SQL = """
SELECT repo,
       SUM(CASE WHEN workflow_name LIKE '%ealth%' THEN 1 ELSE 0 END) AS health_check_runs,
       SUM(CASE WHEN workflow_name LIKE '%eploy%' THEN 1 ELSE 0 END) AS deploy_runs,
       SUM(CASE WHEN workflow_name LIKE '%can%' THEN 1 ELSE 0 END) AS scan_runs,
       COUNT(DISTINCT workflow_name) AS distinct_workflows
FROM github.ci_runs
GROUP BY repo
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    has_workflows = {r["repo"]: r["present"] for r in con.execute(
        "SELECT repo, present FROM detectors.presence WHERE snapshot='head' AND artifact='github_workflows'"
    ).fetchall()}
    return [dict(r, has_workflows_dir=has_workflows.get(r["repo"])) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
