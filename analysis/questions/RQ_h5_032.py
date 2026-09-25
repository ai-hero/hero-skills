"""Q7.xx / RQ-h5-032 -- How does the agent-memory corpus grow over time, by
volume and type, and what share carries a stated reason (has_why)?

`type` is NULL for any memory file with no YAML frontmatter -- ingest/harness.py
reads it from a `type:` key in the file's own frontmatter block, and a plain
note under ~/.claude/projects/*/memory/*.md parses with type=None rather than
a wrong guess. Read month-over-month volume/chars as the reliable trend; the
type breakdown covers only the rows that have a frontmatter type.
"""
RQ_ID = "RQ-h5-032"
QUESTION = "How does the agent-memory corpus grow over time, by volume and type?"

SQL = """
SELECT substr(created_ts, 1, 7) AS month, type, COUNT(*) AS memories,
       SUM(chars) AS total_chars, SUM(has_why) AS with_why
FROM harness.memories
WHERE created_ts IS NOT NULL
GROUP BY month, type
ORDER BY month
"""


def answer(con):
    return con.execute(SQL).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
