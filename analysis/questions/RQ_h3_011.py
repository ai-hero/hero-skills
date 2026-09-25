"""Q11.xx / RQ-h3-011 -- How often does work planned from the design
record act on design information that's already stale? Proxy: items
created after the repo's DESIGN.md was last touched by more than 30 days
(planning against an aging record).
"""
RQ_ID = "RQ-h3-011"
QUESTION = "How often does work planned from the design record act on design information that's already stale?"


def answer(con):
    import datetime as dt
    last_touch = {r["repo"]: r["ts"] for r in con.execute(
        "SELECT repo, MAX(ts) AS ts FROM knowledge.doc_versions WHERE doc = 'DESIGN.md' GROUP BY repo"
    ).fetchall()}
    items = con.execute("SELECT repo, created_ts FROM plans.plan_items WHERE created_ts IS NOT NULL").fetchall()
    stale = total = 0
    for r in items:
        touch = last_touch.get(r["repo"])
        if not touch:
            continue
        total += 1
        gap = (dt.datetime.fromisoformat(r["created_ts"]) - dt.datetime.fromisoformat(touch)).days
        if gap > 30:
            stale += 1
    return [{"items_checked": total, "planned_against_design_md_older_than_30d": stale,
             "share": round(stale / total, 3) if total else None}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
