"""Q99.xx / NEW-CH11-03 -- How does the owner's perceived speed-up
compare with the measured change in throughput, set against the actual
spend? sql half: month-by-month merged-PR throughput and spend, the
measured side of the comparison. The owner's *perceived* speedup is not
in any ingested table -- it would have to be elicited from the owner
directly, which this file cannot do.
"""
RQ_ID = "NEW-CH11-03"
QUESTION = "How does the owner's perceived speed-up compare with the measured change in throughput, against actual spend?"


def answer(con):
    throughput = con.execute(
        "SELECT strftime('%Y-%m', merged_ts) AS month, COUNT(*) AS merged_prs "
        "FROM github.prs WHERE merged_ts IS NOT NULL GROUP BY 1 ORDER BY 1"
    ).fetchall()
    spend = con.execute(
        "SELECT repo, SUM(cost_usd) AS cost_usd FROM detectors.session_spend GROUP BY repo ORDER BY cost_usd DESC"
    ).fetchall()
    return [{"measured_monthly_throughput": [dict(r) for r in throughput],
             "measured_spend_by_repo": [dict(r) for r in spend]},
            {"answerable_by_code": "partial",
             "reason": "the measured side (throughput and spend by month) is above; the owner's "
                       "*perceived* speedup is not in any ingested table and needs to be asked "
                       "directly, not computed"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
