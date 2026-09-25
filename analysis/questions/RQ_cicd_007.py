"""Q15.xx / RQ-cicd-007 -- Does running more agent sessions in parallel
lengthen CI queue time? Correlates the peak-concurrency signal (RQ-h6-019)
with mean CI run duration per week -- a coarse fleet-wide check, not a
per-run causal link (no run<->session join exists).
"""
RQ_ID = "RQ-cicd-007"
QUESTION = "Does running more agent sessions in parallel lengthen CI queue time?"


def answer(con):
    sessions_by_week = {r["week"]: r["n"] for r in con.execute(
        "SELECT week, COUNT(*) AS n FROM harness.sessions WHERE week IS NOT NULL GROUP BY week"
    ).fetchall()}
    ci_by_week = {r["week"]: r["avg_s"] for r in con.execute(
        "SELECT week, AVG(duration_s) AS avg_s FROM github.ci_runs WHERE week IS NOT NULL GROUP BY week"
    ).fetchall()}
    weeks = sorted(set(sessions_by_week) & set(ci_by_week))
    return [{"week": w, "sessions": sessions_by_week[w], "avg_ci_run_seconds": round(ci_by_week[w], 1)}
            for w in weeks]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
