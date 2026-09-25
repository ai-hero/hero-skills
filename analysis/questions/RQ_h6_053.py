"""Q3.13 / RQ-h6-053 -- How often does the factory hit a session, weekly or
plan usage limit, and how long does each stall last?

Raw limit_events fires several rows per real stall (retries hitting the
same wall seconds apart, not separate outages), so events of the same kind within 5
minutes of each other are merged into one stall, keyed by its earliest ts.
Stall duration = time from that ts to the next prompt anywhere in the
fleet (harness.prompts, any repo) -- "when did any work resume," which is
what a limit-driven outage of the whole factory means, not just that one
session.

Caveat this surfaces rather than hides: a limit hit late in the day or
before a weekend measures as an hours-long stall even when the real cause
was the owner logging off, not the limit -- the data can't distinguish
"blocked by the limit" from "would have stopped anyway." Read a single
week's average stall time with that in mind; the stall *count* per kind is
unaffected by this ambiguity.
"""
import datetime as dt

RQ_ID = "RQ-h6-053"
QUESTION = "How often does the factory hit a usage limit, and how long does each stall last?"

MERGE_WINDOW_MIN = 5


def _parse(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def answer(con):
    events = con.execute("SELECT ts, kind FROM harness.limit_events ORDER BY kind, ts").fetchall()
    prompts = sorted(_parse(r["ts"]) for r in con.execute("SELECT ts FROM harness.prompts").fetchall())

    stalls = []
    last_ts_by_kind = {}
    for ts, kind in events:
        t = _parse(ts)
        last = last_ts_by_kind.get(kind)
        if last and (t - last).total_seconds() <= MERGE_WINDOW_MIN * 60:
            last_ts_by_kind[kind] = t
            continue  # part of the same stall, already counted
        last_ts_by_kind[kind] = t
        stalls.append((kind, t))

    import bisect
    out_rows = []
    for kind, t in stalls:
        i = bisect.bisect_right(prompts, t)
        resumed = prompts[i] if i < len(prompts) else None
        stall_minutes = round((resumed - t).total_seconds() / 60, 1) if resumed else None
        y, w, _ = t.isocalendar()
        out_rows.append({"week": f"{y}-W{w:02d}", "kind": kind, "stall_start": t.isoformat(),
                          "stall_minutes": stall_minutes})

    by_week_kind = {}
    for r in out_rows:
        key = (r["week"], r["kind"])
        b = by_week_kind.setdefault(key, {"n": 0, "total_min": 0.0})
        b["n"] += 1
        b["total_min"] += r["stall_minutes"] or 0

    summary = [
        {"week": w, "kind": k, "stalls": v["n"], "total_stall_minutes": round(v["total_min"], 1),
         "avg_stall_minutes": round(v["total_min"] / v["n"], 1)}
        for (w, k), v in sorted(by_week_kind.items())
    ]
    return summary


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
