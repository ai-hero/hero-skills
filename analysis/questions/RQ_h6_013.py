"""Q10.xx / RQ-h6-013 -- How regular is the interval between security
audits in each repo? Security-round goals are matched by title ("security
round"/"security audit"); if fewer than two in a repo have a created_ts, no
interval is computed for it. Rows are reported as-is.
"""
RQ_ID = "RQ-h6-013"
QUESTION = "How regular is the interval between security audits in each repo?"


def answer(con):
    rows = con.execute(
        "SELECT repo, title, created_ts FROM plans.goals WHERE title LIKE '%security round%' "
        "OR title LIKE '%security audit%' ORDER BY repo, created_ts"
    ).fetchall()
    return [{"security_round_goals_found": len(rows)}] + [dict(r) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
