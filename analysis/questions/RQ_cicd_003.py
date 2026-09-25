"""Q15.xx / RQ-cicd-003 -- What share of CI failures pass on a re-run with
no code change, and which checks produce the most of them?

A "re-run with no code change" = two ci_runs rows for the same (repo,
workflow_name, head_sha), one that failed and a later one (by created_ts)
that succeeded -- same commit, so nothing in the code changed between them.
This under-counts: a failure followed only by more failures on that sha
never gets re-run successfully and so never shows up as "passed on re-run,"
which is correct (it didn't), but also misses a failure that was fixed by
force-pushing a code change onto the same branch under a NEW sha -- that's
a real fix, not a flake, and correctly excluded here.
"""
RQ_ID = "RQ-cicd-003"
QUESTION = "What share of CI failures pass on a re-run with no code change, and which checks flake most?"

SQL = """
SELECT repo, workflow_name, head_sha, conclusion, created_ts
FROM github.ci_runs
WHERE conclusion IN ('failure', 'success')
ORDER BY repo, workflow_name, head_sha, created_ts
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    groups = {}
    for r in rows:
        groups.setdefault((r["repo"], r["workflow_name"], r["head_sha"]), []).append(r["conclusion"])

    total_failures = flaked = 0
    by_workflow = {}
    for (repo, workflow, sha), conclusions in groups.items():
        for i, c in enumerate(conclusions):
            if c != "failure":
                continue
            total_failures += 1
            w = by_workflow.setdefault(workflow, {"failures": 0, "flaked": 0})
            w["failures"] += 1
            if "success" in conclusions[i + 1:]:
                flaked += 1
                w["flaked"] += 1

    per_workflow = [
        {"workflow_name": w, "failures": v["failures"], "flaked_then_passed": v["flaked"],
         "flake_rate": round(v["flaked"] / v["failures"], 3) if v["failures"] else None}
        for w, v in sorted(by_workflow.items(), key=lambda kv: -kv[1]["flaked"])
    ]
    summary = {"total_failures": total_failures, "flaked_then_passed": flaked,
               "flake_share_of_failures": round(flaked / total_failures, 3) if total_failures else None}
    return [summary] + per_workflow


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
