"""Q3.01 / RQ-h6-050 -- What is total agent spend, and how does it split
between the main thread and subagents?

subagent_runs.cost_usd_est is a component of its parent session's cost_usd,
not additive on top of it (ingest/harness.py reads cost_usd from Claude
Code's own cost-state totalCostUSD where available, "cost-state" -- which
already includes subagent spend; a session with no cost-state file gets a
token-based estimate instead, "priced"). So: main_thread_spend = session cost minus the
estimated subagent share, and the "_est" in subagent cost means the split
is approximate even where the session total is authoritative.
"""
RQ_ID = "RQ-h6-050"
QUESTION = "What is total agent spend, and how does it split between the main thread and subagents?"

SQL = """
SELECT s.cost_method,
       COUNT(DISTINCT s.session_id_hash) AS sessions,
       ROUND(SUM(s.cost_usd), 2) AS total_cost,
       ROUND(SUM(sub.subagent_cost), 2) AS subagent_cost_est,
       ROUND(SUM(s.cost_usd) - SUM(sub.subagent_cost), 2) AS main_thread_cost_est
FROM harness.sessions s
LEFT JOIN (
    SELECT session_id_hash, SUM(cost_usd_est) AS subagent_cost
    FROM harness.subagent_runs GROUP BY session_id_hash
) sub ON sub.session_id_hash = s.session_id_hash
GROUP BY s.cost_method
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    total = sum(r["total_cost"] for r in rows)
    sub_total = sum(r["subagent_cost_est"] or 0 for r in rows)
    out = [dict(r) for r in rows]
    out.append({
        "cost_method": "ALL",
        "sessions": sum(r["sessions"] for r in rows),
        "total_cost": round(total, 2),
        "subagent_cost_est": round(sub_total, 2),
        "main_thread_cost_est": round(total - sub_total, 2),
        "subagent_share": round(sub_total / total, 3) if total else None,
    })
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
