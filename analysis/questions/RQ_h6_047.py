"""Q3.05 / RQ-h6-047 -- Is the convention of investigating in a subagent, to
keep the main context small, followed in practice?
Proxy: share of read-heavy tool calls (Read, Grep, Glob, Bash) issued from
the main thread (subagent_type IS NULL) vs delegated into an Explore/
general-purpose subagent (subagent_type IS NOT NULL). Doesn't distinguish
"investigation" from other subagent work, so this reads as a ceiling on
delegated investigation, not an exact rate.
"""
RQ_ID = "RQ-h6-047"
QUESTION = "Is the convention of investigating in a subagent, to keep main context small, followed in practice?"

READ_HEAVY_TOOLS = ("Read", "Grep", "Glob", "Bash")

SQL = """
SELECT tool, CASE WHEN subagent_type IS NULL THEN 'main_thread' ELSE 'subagent' END AS location,
       COUNT(*) AS calls
FROM harness.tool_calls
WHERE tool IN ('Read', 'Grep', 'Glob', 'Bash', 'Task')
GROUP BY tool, location
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    main = sum(r["calls"] for r in rows if r["location"] == "main_thread" and r["tool"] in READ_HEAVY_TOOLS)
    sub = sum(r["calls"] for r in rows if r["location"] == "subagent" and r["tool"] in READ_HEAVY_TOOLS)
    total = main + sub
    return [dict(r) for r in rows] + [{
        "read_heavy_calls_on_main_thread": main, "read_heavy_calls_in_subagents": sub,
        "delegated_share": round(sub / total, 3) if total else None,
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
