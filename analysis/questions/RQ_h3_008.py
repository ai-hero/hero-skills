"""Q11.xx / RQ-h3-008 -- What is the distribution of time between a defect
being introduced and being fixed? D5-backed: uses the same-file-touched-
within-14d lag from detectors.followups as the fix-time proxy (a follow-up
isn't necessarily a bug fix -- see the caveat already in d5_followups.py's
own docstring; this is the fullest available distribution, not a defect-
only one).
"""
RQ_ID = "RQ-h3-008"
QUESTION = "What is the distribution of time between a defect being introduced and being fixed?"


def answer(con):
    rows = con.execute(
        "SELECT followup_within_14d_days FROM detectors.followups WHERE followup_within_14d_days IS NOT NULL"
    ).fetchall()
    days = sorted(r[0] for r in rows)
    n = len(days)
    if not n:
        return [{"note": "no follow-up-fix pairs found"}]
    return [{
        "n": n, "p10_days": days[int(n * 0.1)], "median_days": days[n // 2],
        "p90_days": days[int(n * 0.9)], "max_days": days[-1],
        "note": "proxy via D5's same-file-within-14d heuristic, not a confirmed defect/fix pairing",
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
