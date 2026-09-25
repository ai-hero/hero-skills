"""Q9.xx / RQ-h1-035 -- What share of merged changes need a follow-up fix
or revert within days, and has that changed over the study? D5-backed.
"""
RQ_ID = "RQ-h1-035"
QUESTION = "What share of merged changes need a follow-up fix or revert within days, and has that changed over time?"

SQL = "SELECT substr(merged_ts, 1, 7) AS month, followup_within_14d_days, reopened FROM detectors.followups"


def answer(con):
    rows = con.execute(SQL).fetchall()
    by_month = {}
    for r in rows:
        b = by_month.setdefault(r["month"], {"prs": 0, "followed_up": 0, "reopened": 0})
        b["prs"] += 1
        b["followed_up"] += r["followup_within_14d_days"] is not None
        b["reopened"] += r["reopened"]
    return [{"month": m, **v, "followup_share": round(v["followed_up"] / v["prs"], 3)}
            for m, v in sorted(by_month.items())]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
