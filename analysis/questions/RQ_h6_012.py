"""Q10.xx / RQ-h6-012 -- How often is the idea-grilling step run before a
goal starts, versus skipped?
Proxy: tool_calls.skill_name invocation counts for wayfare-grill-idea vs
wayfare-start-goal (both hero-skills: and wayfare: naming eras counted
together) -- an upper bound on the "run before" rate, since this counts
totals, not verified same-goal pairing.
"""
RQ_ID = "RQ-h6-012"
QUESTION = "How often is the idea-grilling step run before a goal starts, versus skipped?"

SQL = """
SELECT skill_name, COUNT(*) AS invocations
FROM harness.tool_calls
WHERE skill_name LIKE '%wayfare-grill-idea%' OR skill_name LIKE '%wayfare-start-goal%'
GROUP BY skill_name
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    grill = sum(r["invocations"] for r in rows if "grill-idea" in r["skill_name"])
    start = sum(r["invocations"] for r in rows if "start-goal" in r["skill_name"])
    return [dict(r) for r in rows] + [{
        "grill_idea_invocations": grill, "start_goal_invocations": start,
        "grill_per_goal_start_upper_bound": round(grill / start, 3) if start else None,
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
