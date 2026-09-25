"""Q9.xx / RQ-h1-022 -- How many work items are created and closed per week,
by category (feature, defect, security, ...)?

"Closed" here is status done/delivered/dropped -- created_ts/done_ts are the
only lifecycle timestamps ingest/plans.py extracts, so this reports opened-
per-week from created_ts and closed-per-week from done_ts, not a true
in-flight count (an item open but never closed has no closed week at all).

Week keys must come from fleet.dims() (ISO week), not sqlite's strftime
%W (Sunday-start, non-ISO) -- mixing the two would silently misalign the
opened and closed columns on weeks that straddle the definitions' different
week-start days.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import dims

RQ_ID = "RQ-h1-022"
QUESTION = "How many work items are created and closed per week, by category?"

CLOSED_STATUSES = ("done", "delivered", "dropped")

OPENED_SQL = """
SELECT week, type, COUNT(*) AS opened
FROM plans.plan_items
WHERE type != 'goal' AND week IS NOT NULL
GROUP BY week, type
"""

CLOSED_RAW_SQL = f"""
SELECT done_ts, type
FROM plans.plan_items
WHERE type != 'goal' AND status IN {CLOSED_STATUSES} AND done_ts IS NOT NULL
"""


def answer(con):
    opened = {(w, t): n for w, t, n in con.execute(OPENED_SQL).fetchall()}
    closed = {}
    for done_ts, type_ in con.execute(CLOSED_RAW_SQL).fetchall():
        week = dims(done_ts)["week"]
        closed[(week, type_)] = closed.get((week, type_), 0) + 1
    out = []
    for week, type_ in sorted(set(opened) | set(closed)):
        out.append({
            "week": week, "type": type_,
            "opened": opened.get((week, type_), 0),
            "closed": closed.get((week, type_), 0),
        })
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
