"""Q14.xx / NEW-C08-A -- Is new control coverage being added faster,
steadily, or slower over time?

register_history's `file` column is "repo:filename" (the register overlay
is per-repo, e.g. each repo commits its own CONTROLS.yaml/CHECKS.yaml on its
own schedule -- these are NOT one fleet-wide synchronized sync). Rows from
different repos land seconds apart, so grouping by exact timestamp fragments;
this buckets by day and takes the max controls/checks count seen fleet-wide
that day. It is a floor: only syncs captured in git history are counted, not
a continuous series.
"""
RQ_ID = "NEW-C08-A"
QUESTION = "Is new control coverage being added faster, steadily, or slower over time?"

SQL = """
SELECT substr(ts, 1, 10) AS day,
       MAX(CASE WHEN file LIKE '%CONTROLS.yaml' THEN controls END) AS max_controls_seen,
       MAX(CASE WHEN file LIKE '%CHECKS.yaml' THEN checks END) AS max_checks_seen,
       COUNT(DISTINCT substr(file, 1, instr(file, ':') - 1)) AS repos_synced_that_day
FROM knowledge.register_history
GROUP BY day
ORDER BY day
"""


def answer(con):
    return con.execute(SQL).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
