"""Q10.xx / RQ-h6-015 -- How often is a recorded one-way-door design
decision later reversed?

No "reversed" flag exists anywhere -- this reports the one_way_door value
distribution itself. A raw value that failed to parse (e.g. "true # <comment>",
a YAML inline-comment artifact) is reported as its own bucket rather than
silently coerced to True or dropped.
"""
RQ_ID = "RQ-h6-015"
QUESTION = "How often is a recorded one-way-door design decision later reversed?"


def answer(con):
    import json
    rows = con.execute("SELECT raw_frontmatter_json FROM plans.plan_items WHERE raw_frontmatter_json LIKE '%one_way_door%'").fetchall()
    counts = {}
    for (raw,) in rows:
        try:
            v = str(json.loads(raw).get("one_way_door"))
        except (json.JSONDecodeError, TypeError):
            v = "(parse error)"
        counts[v] = counts.get(v, 0) + 1
    return [{"one_way_door_value": k, "items": v} for k, v in counts.items()] + [
        {"note": "no reversal-tracking field exists; this is the value distribution only"}
    ]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
