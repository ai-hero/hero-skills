"""Q9.xx / RQ-h1-036 -- When the same small change is needed across many
repos, is it done by one agent sweeping the fleet, or independently by
several? Same D7 cluster signal as RQ-h6-002: a cluster's commits landing
within a short span of each other (hours, not days) reads as one sweep; a
cluster spread across many days reads as independent, repeated discovery.
"""
RQ_ID = "RQ-h1-036"
QUESTION = "Is the same small change swept across repos by one agent, or found independently by several?"

SWEEP_WINDOW_HOURS = 6


def answer(con):
    rows = con.execute("SELECT cluster_id, ts FROM detectors.duplicate_fixes ORDER BY cluster_id, ts").fetchall()
    import datetime as dt
    clusters = {}
    for r in rows:
        clusters.setdefault(r["cluster_id"], []).append(dt.datetime.fromisoformat(r["ts"]))

    sweep, independent = 0, 0
    for cid, times in clusters.items():
        span_hours = (max(times) - min(times)).total_seconds() / 3600
        if span_hours <= SWEEP_WINDOW_HOURS:
            sweep += 1
        else:
            independent += 1
    total = sweep + independent
    return [{"clusters": total, "likely_single_sweep": sweep, "likely_independent_discovery": independent,
             "sweep_share": round(sweep / total, 3) if total else None}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
