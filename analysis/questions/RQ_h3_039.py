"""Q9.xx / RQ-h3-039 -- Of the security findings only a manual audit
surfaced, how many were caught before shipping, and does that share
change over time? sql half: security-kind gate firings by verdict and
month, as the closest proxy for "manual audit" findings this repo
tracks (wayfare-audit-security's own runs). Whether a given finding
would otherwise have been missed by automation needs a human read.
"""
RQ_ID = "RQ-h3-039"
QUESTION = "Of security findings only a manual audit surfaced, how many were caught before shipping, and does that share change over time?"


def answer(con):
    rows = con.execute(
        "SELECT strftime('%Y-%m', ts) AS month, verdict, COUNT(*) AS n "
        "FROM detectors.gate_firings WHERE gate_kind LIKE '%security%' GROUP BY 1, 2 ORDER BY 1"
    ).fetchall()
    by_month = {}
    for r in rows:
        by_month.setdefault(r["month"], {})[r["verdict"]] = r["n"]
    return [{"month": m, **counts} for m, counts in sorted(by_month.items())] + [
        {"answerable_by_code": "partial",
         "reason": "security-gate firing volume and pass/fail split by month is above; whether a "
                   "given failure was something *only* a manual audit (vs automated scan) would "
                   "have caught needs a human read of each finding's source"}
    ]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
