"""Q14.xx / RQ-h5-021 -- How long does a mirrored compliance summary stay
out of sync with its source? register_history's CONSISTENCY.md rows give
a generated-at timestamp per sync; "out of sync" duration would need a
source-changed timestamp to compare against, which isn't tracked
separately from the sync itself (the generated file IS the record).
"""
RQ_ID = "RQ-h5-021"
QUESTION = "How long does a mirrored compliance summary stay out of sync with its source?"


def answer(con):
    rows = con.execute(
        "SELECT ts FROM knowledge.register_history WHERE file LIKE '%CONSISTENCY.md' ORDER BY ts"
    ).fetchall()
    if len(rows) < 2:
        return [{"note": "fewer than 2 CONSISTENCY.md syncs recorded -- no interval to measure"}]
    import datetime as dt
    gaps = []
    for a, b in zip(rows, rows[1:]):
        gaps.append((dt.datetime.fromisoformat(b[0]) - dt.datetime.fromisoformat(a[0])).total_seconds() / 3600)
    return [{"syncs": len(rows), "median_hours_between_syncs": round(sorted(gaps)[len(gaps) // 2], 1),
             "note": "gap between regenerations, not a source-changed-to-synced lag (no separate source timestamp exists)"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
