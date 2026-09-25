"""Q14.xx / RQ-h5-009 -- How have the control register's size and makeup
(controls, checks, severity mix) changed over time? controls.created_ts is
the git-log-derived add date per control (ingest/knowledge.py); severity
mix from the current snapshot, since there's no severity-over-time history.
"""
RQ_ID = "RQ-h5-009"
QUESTION = "How have the control register's size and makeup changed over time?"


def answer(con):
    rows = con.execute(
        "SELECT substr(created_ts, 1, 7) AS month, COUNT(*) AS controls_added "
        "FROM knowledge.controls WHERE created_ts IS NOT NULL GROUP BY month ORDER BY month"
    ).fetchall()
    severity = con.execute(
        "SELECT severity, COUNT(*) AS n FROM knowledge.controls GROUP BY severity ORDER BY n DESC"
    ).fetchall()
    return [dict(r) for r in rows] + [{"current_severity_mix": {s["severity"]: s["n"] for s in severity}}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
