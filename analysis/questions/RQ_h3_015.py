"""Q11.xx / RQ-h3-015 -- After a merged change, how often does a
follow-up fix against the same scope land, and how quickly? Reframes
RQ-h1-035's D5 data as a rate-and-speed pair instead of a monthly trend.
"""
RQ_ID = "RQ-h3-015"
QUESTION = "After a merged change, how often does a follow-up fix against the same scope land, and how quickly?"


def answer(con):
    rows = con.execute("SELECT followup_within_7d_days, followup_within_14d_days FROM detectors.followups").fetchall()
    total = len(rows)
    within_7 = sum(1 for r in rows if r["followup_within_7d_days"] is not None)
    within_14 = sum(1 for r in rows if r["followup_within_14d_days"] is not None)
    speeds = sorted(r["followup_within_14d_days"] for r in rows if r["followup_within_14d_days"] is not None)
    n = len(speeds)
    return [{
        "merged_prs": total, "followed_up_within_7d": within_7, "followed_up_within_14d": within_14,
        "followup_rate_14d": round(within_14 / total, 3),
        "median_days_to_followup": speeds[n // 2] if n else None,
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
