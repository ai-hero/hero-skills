"""Q13.xx / RQ-h4-022 -- Does each design record follow its own rules:
decisions appended not edited, a header pointing at the source? Proxy for
"appended not edited": design_decisions.first_seen_sha should differ per
decision (each new decision is its own commit); a repo where many
decisions share one first_seen_sha suggests a bulk rewrite rather than
incremental append.
"""
RQ_ID = "RQ-h4-022"
QUESTION = "Does each design record follow its own rules: decisions appended not edited?"

SQL = """
SELECT repo, COUNT(*) AS decisions, COUNT(DISTINCT first_seen_sha) AS distinct_commits
FROM knowledge.design_decisions
GROUP BY repo
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    return [dict(r, decisions_per_commit=round(r["decisions"] / r["distinct_commits"], 2)) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
