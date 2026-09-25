"""Q16.xx / RQ-h2-018 -- When a deploy fails or never happens because CI
went red, how long until it recovers? Deploy-workflow-specific slice of
RQ-cicd-002's red-to-green data.
"""
RQ_ID = "RQ-h2-018"
QUESTION = "When a deploy fails because CI went red, how long until it recovers?"

SQL = """
SELECT repo, workflow_name, head_sha, conclusion, created_ts
FROM github.ci_runs
WHERE workflow_name LIKE '%eploy%' AND conclusion IN ('failure', 'success')
ORDER BY repo, workflow_name, head_sha, created_ts
"""


def answer(con):
    import datetime as dt
    rows = con.execute(SQL).fetchall()
    groups = {}
    for r in rows:
        groups.setdefault((r["repo"], r["workflow_name"], r["head_sha"]), []).append((r["conclusion"], r["created_ts"]))
    recoveries = []
    for seq in groups.values():
        for i, (concl, ts) in enumerate(seq):
            if concl != "failure":
                continue
            for concl2, ts2 in seq[i + 1:]:
                if concl2 == "success":
                    hours = (dt.datetime.fromisoformat(ts2.replace("Z", "+00:00")) -
                             dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))).total_seconds() / 3600
                    recoveries.append(hours)
                    break
    if not recoveries:
        return [{"note": "no deploy-workflow failure-then-success pairs found"}]
    recoveries.sort()
    n = len(recoveries)
    return [{"deploy_failures_that_recovered": n, "median_hours_to_recover": round(recoveries[n // 2], 2),
             "max_hours_to_recover": round(recoveries[-1], 2)}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
