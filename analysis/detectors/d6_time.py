"""D6 time segmentation -> .analysis/data/detectors.sqlite, table session_time_segments.

Cuts each session's activity into working / waiting_human / limited / away,
from turns.ts as the activity clock (both roles), asks.ts and limit_events.ts
as the two things that explain a gap. Per gap between consecutive turns:
  - <= 5 min: working (thinking/tool time within a normal exchange)
  - > 5 min and an ask fired inside the gap: waiting_human
  - > 5 min and no ask but a limit_event fired inside the gap: limited
  - > 5 min, neither: away (owner stepped away, for no recorded reason)

This is an approximation, not ground truth: asks/limit_events have no
explicit "resolved at" timestamp, so a gap is attributed to whichever of the
two events falls inside it, and a gap with BOTH an ask and a limit event in
it is credited to the ask (asks are rarer and more specific than the
catch-all "away" bucket, so under-crediting waiting_human is the safer
error). No CI sub-state -- linking a gap to a specific CI run in progress
needs a branch/run join this pass doesn't do.
"""
import datetime as dt
import os, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import OUT

DB_PATH = os.path.join(OUT, "detectors.sqlite")
HARNESS_DB = os.path.join(OUT, "harness.sqlite")
WORKING_GAP_MIN = 5


def _parse(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def build():
    if not os.path.exists(HARNESS_DB):
        sys.exit("detectors/d6_time.py needs .analysis/data/harness.sqlite -- run ingest/harness.py first")

    hcon = sqlite3.connect(HARNESS_DB)
    turns = hcon.execute("SELECT session_id_hash, ts FROM turns WHERE ts IS NOT NULL ORDER BY session_id_hash, ts").fetchall()
    asks_by_session, limits_by_session = {}, {}
    for sid, ts in hcon.execute("SELECT session_id_hash, ts FROM asks WHERE ts IS NOT NULL").fetchall():
        asks_by_session.setdefault(sid, []).append(_parse(ts))
    for sid, ts in hcon.execute("SELECT session_id_hash, ts FROM limit_events WHERE ts IS NOT NULL").fetchall():
        limits_by_session.setdefault(sid, []).append(_parse(ts))

    by_session = {}
    for sid, ts in turns:
        by_session.setdefault(sid, []).append(_parse(ts))

    out = []
    for sid, times in by_session.items():
        asks = sorted(asks_by_session.get(sid, []))
        limits = sorted(limits_by_session.get(sid, []))
        for a, b in zip(times, times[1:]):
            gap_min = (b - a).total_seconds() / 60
            if gap_min <= WORKING_GAP_MIN:
                out.append((sid, "working", a.isoformat(), b.isoformat(), round(gap_min, 2)))
                continue
            if any(a <= t <= b for t in asks):
                kind = "waiting_human"
            elif any(a <= t <= b for t in limits):
                kind = "limited"
            else:
                kind = "away"
            out.append((sid, kind, a.isoformat(), b.isoformat(), round(gap_min, 2)))

    con = sqlite3.connect(DB_PATH)
    con.execute("DROP TABLE IF EXISTS session_time_segments")
    con.execute("""
        CREATE TABLE session_time_segments (
            session_id_hash TEXT, kind TEXT, start_ts TEXT, end_ts TEXT, minutes REAL
        )
    """)
    con.executemany("INSERT INTO session_time_segments VALUES (?,?,?,?,?)", out)
    con.commit()

    totals = {}
    for row in out:
        totals[row[1]] = totals.get(row[1], 0) + row[4]
    print(f"detectors.sqlite: session_time_segments {len(out)} rows across {len(by_session)} sessions")
    for kind, minutes in sorted(totals.items(), key=lambda kv: -kv[1]):
        print(f"  {kind}: {minutes/60:.1f} hours")
    con.close()
    hcon.close()


if __name__ == "__main__":
    build()
