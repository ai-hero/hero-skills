"""Q3.03 / RQ-h6-051 -- How does the main-thread model mix change week to
week, and how quickly is a newly released model adopted?

turns is main-thread only (subagent activity lives in subagent_runs, joined
separately by any question that needs it), so grouping turns by week/model
directly answers the mix question. Adoption speed vs model_releases is left
as a follow-up join, not computed here.
"""
RQ_ID = "RQ-h6-051"
QUESTION = "How does the main-thread model mix change week to week?"

SQL = """
SELECT strftime('%Y-%m', ts) AS month, model, COUNT(*) AS turns
FROM harness.turns
WHERE role = 'assistant' AND model IS NOT NULL AND model != '<synthetic>'
GROUP BY month, model
ORDER BY month, turns DESC
"""


def answer(con):
    return con.execute(SQL).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
