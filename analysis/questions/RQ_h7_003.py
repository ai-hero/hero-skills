"""Q4.08 / RQ-h7-003 -- How long does work sit waiting on a human decision,
and what share of lead time is that wait? D6-backed (session_time_segments).
"""
RQ_ID = "RQ-h7-003"
QUESTION = "How long does work sit waiting on a human decision, and what share of lead time is that wait?"

SQL = "SELECT kind, SUM(minutes) AS minutes FROM detectors.session_time_segments GROUP BY kind"


def answer(con):
    rows = {r["kind"]: r["minutes"] for r in con.execute(SQL).fetchall()}
    total = sum(rows.values())
    return [{"kind": k, "hours": round(v / 60, 1), "share_of_all_session_time": round(v / total, 3)}
            for k, v in sorted(rows.items(), key=lambda kv: -kv[1])]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
