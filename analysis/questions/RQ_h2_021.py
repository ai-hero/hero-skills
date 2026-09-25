"""Q16.xx / RQ-h2-021 -- How much harness usage is wasted: limit hits,
subagent output never used, and away time? Combines D6's away/limited
hours with subagent spend (subagent output being "never used" isn't
directly observable -- reports subagent spend as a share of total instead,
which is the closest available proxy for "time that could have been
wasted").
"""
RQ_ID = "RQ-h2-021"
QUESTION = "How much harness usage is wasted: limit hits, subagent spend share, and away time?"


def answer(con):
    segments = con.execute(
        "SELECT kind, SUM(minutes) AS minutes FROM detectors.session_time_segments GROUP BY kind"
    ).fetchall()
    seg = {r["kind"]: r["minutes"] for r in segments}
    total = sum(seg.values())
    return [{
        "away_hours": round(seg.get("away", 0) / 60, 1), "limited_hours": round(seg.get("limited", 0) / 60, 1),
        "away_and_limited_share_of_session_time": round((seg.get("away", 0) + seg.get("limited", 0)) / total, 3),
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
