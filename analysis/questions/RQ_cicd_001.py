"""Q15.xx / RQ-cicd-001 -- Of the CI minutes spent, what share goes to
runs that cannot change an outcome? Proxy: ci_runs.event = 'schedule'
(a cron run with no PR/push behind it -- nothing for it to gate) as the
clearest "cannot change an outcome" case. issue_comment-triggered runs
(auto-approve reacting to a comment) are a second candidate but genuinely
CAN change an outcome (they gate the merge), so excluded.
"""
RQ_ID = "RQ-cicd-001"
QUESTION = "Of the CI minutes spent, what share goes to runs that cannot change an outcome (scheduled runs)?"


def answer(con):
    row = con.execute(
        "SELECT SUM(duration_s) AS total, "
        "SUM(CASE WHEN event = 'schedule' THEN duration_s ELSE 0 END) AS scheduled "
        "FROM github.ci_runs"
    ).fetchone()
    total, scheduled = row["total"] or 0, row["scheduled"] or 0
    return [{"total_ci_minutes": round(total / 60, 1), "scheduled_run_minutes": round(scheduled / 60, 1),
             "scheduled_share": round(scheduled / total, 3) if total else None,
             "note": "'cannot change an outcome' is scoped to schedule-triggered runs only -- the clearest case"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
