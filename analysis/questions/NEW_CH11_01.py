"""Q11.xx / NEW-CH11-01 -- How does the share of changes the factory ships
without a human touching them compare over time? v_commits.actor='agent'
share by month (a commit with no human actor at all) -- 'touching' here
means authoring, not reviewing (RQ-h7-013 covers review separately).
"""
RQ_ID = "NEW-CH11-01"
QUESTION = "How does the share of changes shipped without a human touching them compare over time?"


def answer(con):
    rows = con.execute(
        "SELECT month, actor, COUNT(*) AS n FROM v_commits WHERE month IS NOT NULL GROUP BY month, actor"
    ).fetchall()
    by_month = {}
    for r in rows:
        by_month.setdefault(r["month"], {}).setdefault(r["actor"], r["n"])
    out = []
    for month, actors in sorted(by_month.items()):
        total = sum(actors.values())
        human_free = actors.get("agent", 0) + actors.get("bot", 0)
        out.append({"month": month, "commits": total, "no_human_author_share": round(human_free / total, 3)})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
