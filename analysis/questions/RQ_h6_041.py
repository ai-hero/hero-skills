"""Q10.xx / RQ-h6-041 -- What decides how many reviewer agents run on a
PR, and does more review catch more real defects? D8-backed: review count
per PR against whether that PR later needed a D5 follow-up (a proxy for
"a real defect got through anyway").
"""
RQ_ID = "RQ-h6-041"
QUESTION = "Does more review catch more real defects?"


def answer(con):
    rows = con.execute(
        "SELECT p.review_count, f.followup_within_14d_days FROM github.prs p "
        "JOIN detectors.followups f ON f.repo = p.repo AND f.number = p.number "
        "WHERE p.review_count IS NOT NULL"
    ).fetchall()
    by_count = {}
    for r in rows:
        b = by_count.setdefault(r["review_count"], {"prs": 0, "followed_up": 0})
        b["prs"] += 1
        b["followed_up"] += r["followup_within_14d_days"] is not None
    return [{"review_count": k, "prs": v["prs"], "followup_rate": round(v["followed_up"] / v["prs"], 3)}
            for k, v in sorted(by_count.items())]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
