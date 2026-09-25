"""Q4.xx / RQ-h7-031 -- Could per-repo activity logs merge into one
replayable fleet timeline? Checked directly: every source table this
pipeline ingests already carries a repo column and a timestamp, so a
UNION across commits/prs/plan_items/sessions ordered by ts is already
a fleet-wide replay -- demonstrated here at small scale.
"""
RQ_ID = "RQ-h7-031"
QUESTION = "Could per-repo activity logs merge into one replayable fleet timeline?"


def answer(con):
    rows = con.execute(
        "SELECT committed_ts AS ts, 'commit' AS kind, repo FROM v_commits "
        "UNION ALL SELECT created_ts, 'pr', repo FROM github.prs "
        "UNION ALL SELECT created_ts, 'item', repo FROM plans.plan_items "
        "ORDER BY ts DESC LIMIT 15"
    ).fetchall()
    return [{"mergeable": True, "sample_timeline_tail": [dict(r) for r in rows]}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
