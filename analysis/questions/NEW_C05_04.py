"""Q10.xx / NEW-C05-04 -- What share of merged PRs need a follow-up fix PR
within 3 days, and is that share rising or falling? D5-backed, a tighter
window than the existing 7d/14d columns -- recomputed here rather than
adding a third column to the detector table.
"""
RQ_ID = "NEW-C05-04"
QUESTION = "What share of merged PRs need a follow-up fix PR within 3 days, and is that share rising or falling?"


def answer(con):
    rows = con.execute("SELECT merged_ts, followup_within_7d_days FROM detectors.followups").fetchall()
    by_month = {}
    for r in rows:
        month = r["merged_ts"][:7]
        b = by_month.setdefault(month, {"prs": 0, "within_3d": 0})
        b["prs"] += 1
        if r["followup_within_7d_days"] is not None and r["followup_within_7d_days"] <= 3:
            b["within_3d"] += 1
    return [{"month": m, "prs": v["prs"], "within_3d_share": round(v["within_3d"] / v["prs"], 3)}
            for m, v in sorted(by_month.items())]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
