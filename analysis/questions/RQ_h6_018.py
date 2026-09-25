"""Q13.xx / RQ-h6-018 -- How many cross-repo messages are sent per week,
and what share is answered?
Cross-repo messaging that never went through plans.messages is not
counted, so this is a floor. Reported as-is, not extrapolated.
"""
RQ_ID = "RQ-h6-018"
QUESTION = "How many cross-repo messages are sent per week, and what share is answered?"


def answer(con):
    rows = con.execute("SELECT status, created_ts FROM plans.messages").fetchall()
    total = len(rows)
    answered = sum(1 for r in rows if r["status"] == "answered")
    by_week = {}
    import sys
    sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
    from ingest.fleet import dims
    for r in rows:
        if r["created_ts"]:
            w = dims(r["created_ts"])["week"]
            by_week[w] = by_week.get(w, 0) + 1
    return [{"total_messages": total, "answered": answered,
             "answered_share": round(answered / total, 3) if total else None,
             "note": "a floor: cross-repo messaging outside plans.messages isn't counted"}] + \
           [{"week": w, "messages": n} for w, n in sorted(by_week.items())]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
