"""Q11.xx / RQ-h3-028 -- When an agent's own change introduces a security
defect, did it reach production before being caught? Proxy: security-type
items created after a deploy-workflow success on that repo within the
prior 7 days (the defect's window overlapping a real deploy).
"""
RQ_ID = "RQ-h3-028"
QUESTION = "When an agent's own change introduces a security defect, did it reach production before being caught?"


def answer(con):
    items = con.execute(
        "SELECT repo, created_ts FROM plans.plan_items WHERE type = 'security' AND created_ts IS NOT NULL"
    ).fetchall()
    reached_prod = 0
    for r in items:
        row = con.execute(
            "SELECT 1 FROM github.ci_runs WHERE repo = ? AND workflow_name LIKE '%eploy%' "
            "AND conclusion = 'success' AND created_ts < ? AND created_ts > datetime(?, '-7 days') LIMIT 1",
            (r["repo"], r["created_ts"], r["created_ts"]),
        ).fetchone()
        reached_prod += bool(row)
    return [{"security_items": len(items), "with_a_recent_deploy_success_before_filing": reached_prod}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
