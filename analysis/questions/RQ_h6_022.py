"""Q10.xx / RQ-h6-022 -- How often is each skill invoked, and what share of
invocations finish without an error?
"""
RQ_ID = "RQ-h6-022"
QUESTION = "How often is each skill invoked, and what share of invocations finish without an error?"

SQL = """
SELECT skill_name, COUNT(*) AS invocations, SUM(is_error) AS errored,
       ROUND(1.0 - SUM(is_error) * 1.0 / COUNT(*), 3) AS clean_share
FROM harness.tool_calls
WHERE skill_name IS NOT NULL
GROUP BY skill_name
ORDER BY invocations DESC
"""


def answer(con):
    return con.execute(SQL).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
