"""Q11.xx / NEW-C07-01 -- Once an agent knows another repo needs a
change, how long until the message to that repo is sent? sql half: D3's
propagation table gives lag_hours from an upstream commit to its
downstream adoption commit, which bounds the total "knows -> shipped"
time but does not isolate the "knows -> message sent" sub-interval,
since no message-send timestamp is ingested separately from the
downstream commit itself.
"""
RQ_ID = "NEW-C07-01"
QUESTION = "Once an agent knows another repo needs a change, how long until the message to that repo is sent?"


def answer(con):
    rows = con.execute(
        "SELECT upstream_repo, downstream_repo, AVG(lag_hours) AS avg_lag_hours, "
        "MIN(lag_hours) AS min_lag_hours, MAX(lag_hours) AS max_lag_hours, COUNT(*) AS n "
        "FROM detectors.propagation GROUP BY upstream_repo, downstream_repo ORDER BY n DESC"
    ).fetchall()
    return [dict(r) for r in rows] + [
        {"answerable_by_code": "partial",
         "reason": "lag_hours bounds upstream-commit-to-downstream-adoption time, an upper bound on "
                   "message-send latency; the message itself (per docs/MESSAGES.md) has no separate "
                   "timestamp ingested, so the send-latency sub-interval isn't isolated"}
    ]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
