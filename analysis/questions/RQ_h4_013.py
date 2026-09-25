"""Q13.xx / RQ-h4-013 -- What does propagating a change to every clone
cost in CI minutes, spend and elapsed time, and does it scale with fleet
size? D3-backed: CI minutes for the downstream commits in the propagation
table, and elapsed time already available as lag_hours.
"""
RQ_ID = "RQ-h4-013"
QUESTION = "What does propagating a change to every clone cost in CI minutes and elapsed time?"


def answer(con):
    rows = con.execute(
        "SELECT p.downstream_repo, p.lag_hours, "
        "(SELECT SUM(duration_s) FROM github.ci_runs cr WHERE cr.repo = p.downstream_repo "
        "AND cr.head_sha = p.downstream_sha) AS ci_seconds "
        "FROM detectors.propagation p"
    ).fetchall()
    total_ci_minutes = sum((r["ci_seconds"] or 0) for r in rows) / 60
    lags = sorted(r["lag_hours"] for r in rows)
    n = len(lags)
    return [{"propagated_arrivals": n, "total_ci_minutes_for_arrival_runs": round(total_ci_minutes, 1),
             "median_lag_hours": lags[n // 2] if n else None}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
