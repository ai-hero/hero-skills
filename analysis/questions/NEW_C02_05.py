"""Q9.xx / NEW-C02-05 -- How are merged change sets distributed across days
of the week and hours of the day?

Uses commit authored_ts (not committer_ts) as the proxy for "when the change
was made" -- a squash-merge sets committed_ts to merge time, which would
otherwise pile every commit onto the PR-merge moment instead of when the
work happened. Day-of-week from strftime is 0=Sunday.
"""
RQ_ID = "NEW-C02-05"
QUESTION = "How are merged change sets distributed across days of the week and hours of the day?"

SQL = """
SELECT
    CAST(strftime('%w', authored_ts) AS INTEGER) AS dow,
    CAST(strftime('%H', authored_ts) AS INTEGER) AS hour,
    COUNT(*) AS commits
FROM git.commits
WHERE authored_ts IS NOT NULL
GROUP BY dow, hour
ORDER BY dow, hour
"""

DOW_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def answer(con):
    rows = con.execute(SQL).fetchall()
    return [{"day": DOW_NAMES[r["dow"]], "hour_utc": r["hour"], "commits": r["commits"]} for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
