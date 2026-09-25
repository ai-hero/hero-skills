"""Q10.xx / RQ-h6-029 -- As skills absorbed more multi-step work, did the
owner's prompts get shorter, and did slash-command use rise?
"""
RQ_ID = "RQ-h6-029"
QUESTION = "As skills absorbed more multi-step work, did prompts get shorter and slash-command use rise?"

SQL = """
SELECT month, COUNT(*) AS prompts, ROUND(AVG(chars), 1) AS avg_chars,
       SUM(is_slash_command) AS slash_commands,
       ROUND(SUM(is_slash_command) * 1.0 / COUNT(*), 3) AS slash_share
FROM harness.prompts
WHERE month IS NOT NULL
GROUP BY month
ORDER BY month
"""


def answer(con):
    return con.execute(SQL).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
