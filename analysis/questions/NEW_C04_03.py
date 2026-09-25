"""Q3.xx / NEW-C04-03 -- How often do two sessions work in the same
checkout at once, and how often does one overwrite or block the other?
sql: session_time_segments overlap detection -- two segments whose
[start_ts, end_ts) windows intersect (the table carries no repo column,
so this is fleet-wide concurrency, not per-checkout). Whether
an overlap actually caused an overwrite/block (vs. two agents peacefully
sharing a worktree) needs a human or Haiku read of what happened.
"""
RQ_ID = "NEW-C04-03"
QUESTION = "How often do two sessions work in the same checkout at once, and how often does one overwrite or block the other?"


def answer(con):
    segs = con.execute(
        "SELECT session_id_hash, kind, start_ts, end_ts FROM detectors.session_time_segments "
        "WHERE start_ts IS NOT NULL AND end_ts IS NOT NULL ORDER BY start_ts"
    ).fetchall()
    overlaps = 0
    active = []
    for s in segs:
        active = [a for a in active if a["end_ts"] > s["start_ts"]]
        if active:
            overlaps += 1
        active.append(s)
    return [{"session_segments": len(segs), "overlapping_segment_pairs_detected": overlaps,
             "answerable_by_code": "partial",
             "reason": "time-window overlap between session segments is computed above, but the "
                       "table has no repo column so this can't confirm the overlap was in the *same "
                       "checkout*; and whether an overlap caused an actual overwrite or block needs "
                       "a human or Haiku read of what changed"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
