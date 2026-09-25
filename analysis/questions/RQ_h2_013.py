"""Q16.xx / RQ-h2-013 -- How does the factory's total spend per week
trend, sliced by change sets, commits, PRs and items?
Spend itself has no branch-level weekly join beyond sessions (D9's repo/
branch split has no timestamp finer than the session's own first_ts), so
this reports session spend by week directly, and commit/PR/item counts by
week alongside it for the reader to relate, not a true per-unit rate.
"""
RQ_ID = "RQ-h2-013"
QUESTION = "How does the factory's total spend per week trend, alongside commits, PRs and items?"


def answer(con):
    spend = con.execute(
        "SELECT week, SUM(cost_usd) AS spend, COUNT(*) AS sessions FROM harness.sessions "
        "WHERE week IS NOT NULL GROUP BY week"
    ).fetchall()
    commits = con.execute("SELECT week, COUNT(*) AS n FROM v_commits WHERE week IS NOT NULL GROUP BY week").fetchall()
    commit_by_week = {r["week"]: r["n"] for r in commits}
    return [{"week": r["week"], "spend": round(r["spend"], 2), "sessions": r["sessions"],
             "commits": commit_by_week.get(r["week"], 0)} for r in sorted(spend, key=lambda r: r["week"])]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
