"""Q10.xx / RQ-h6-014 -- When a shared dependency renames or breaks its
reference, how many days pass before every affected repo catches up?
D3-backed proxy: same question as RQ-h6-003 but fleet-wide (any upstream),
not just template/plugin -- "shared dependency" isn't a distinct source in
this data, so any propagated commit is treated as a candidate instance.
"""
RQ_ID = "RQ-h6-014"
QUESTION = "How many days pass before every affected repo catches up on a shared change?"

SQL = "SELECT upstream_repo, downstream_repo, lag_hours FROM detectors.propagation"


def answer(con):
    rows = con.execute(SQL).fetchall()
    lags = sorted(r["lag_hours"] for r in rows)
    n = len(lags)
    if not n:
        return [{"note": "no propagation matches found"}]
    return [{
        "matched_arrivals": n,
        "median_lag_hours": lags[n // 2],
        "p90_lag_hours": lags[int(n * 0.9)],
        "max_lag_hours": lags[-1],
        "max_lag_days": round(lags[-1] / 24, 1),
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
