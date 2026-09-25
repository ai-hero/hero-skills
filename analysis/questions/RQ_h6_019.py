"""Q10.xx / RQ-h6-019 -- How many concurrent agent sessions on one machine
does it take before resource contention shows up?
Reports the concurrency distribution (max sessions with overlapping
[first_ts, last_ts] windows, sampled at each session start) -- does not
correlate it with a contention signal (no resource-usage metric is
ingested), so this answers "how many run concurrently," not "at what count
contention starts."
"""
RQ_ID = "RQ-h6-019"
QUESTION = "How many concurrent agent sessions run at once, at peak?"


def answer(con):
    rows = con.execute("SELECT session_id_hash, first_ts, last_ts FROM harness.sessions "
                        "WHERE first_ts IS NOT NULL AND last_ts IS NOT NULL").fetchall()
    events = []
    for r in rows:
        events.append((r["first_ts"], 1))
        events.append((r["last_ts"], -1))
    events.sort()
    concurrent, peak, peak_ts = 0, 0, None
    from collections import Counter
    histogram = Counter()
    for ts, delta in events:
        concurrent += delta
        histogram[concurrent] += 1
        if concurrent > peak:
            peak, peak_ts = concurrent, ts
    return [{"peak_concurrent_sessions": peak, "peak_at": peak_ts}] + \
           [{"concurrency_level": k, "event_count": v} for k, v in sorted(histogram.items())]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
