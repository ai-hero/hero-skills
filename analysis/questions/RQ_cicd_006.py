"""Q15.xx / RQ-cicd-006 -- Which required checks have never been observed
failing, and is each one able to fail at all? D8-backed via ci_runs
workflow-level pass/fail history (same grouping as RQ_cicd_003.py).
"""
RQ_ID = "RQ-cicd-006"
QUESTION = "Which required checks have never been observed failing?"


def answer(con):
    rows = con.execute(
        "SELECT workflow_name, conclusion, COUNT(*) AS n FROM github.ci_runs "
        "WHERE conclusion IN ('success', 'failure') GROUP BY workflow_name, conclusion"
    ).fetchall()
    by_wf = {}
    for r in rows:
        by_wf.setdefault(r["workflow_name"], {"success": 0, "failure": 0})[r["conclusion"]] = r["n"]
    never_failed = [{"workflow_name": wf, "successes": v["success"], "failures": v["failure"]}
                     for wf, v in by_wf.items() if v["failure"] == 0 and v["success"] >= 5]
    return sorted(never_failed, key=lambda x: -x["successes"])


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
