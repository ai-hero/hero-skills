"""Q17.xx / RQ-h2-028 -- What share of the factory's committed work is
upkeep (dependency updates, compliance, re-verification) versus new
product surface? Reuses RQ-h5-001's item-type split at fleet scale instead
of per-clone.
"""
RQ_ID = "RQ-h2-028"
QUESTION = "What share of the factory's committed work is upkeep versus new product surface?"

UPKEEP_TYPES = ("chore", "security", "docs")


def answer(con):
    rows = con.execute("SELECT type, COUNT(*) AS n FROM plans.plan_items WHERE type != 'goal' GROUP BY type").fetchall()
    upkeep = sum(r["n"] for r in rows if r["type"] in UPKEEP_TYPES)
    total = sum(r["n"] for r in rows)
    return [{"total_items": total, "upkeep_items": upkeep, "upkeep_share": round(upkeep / total, 3)}] + \
           [dict(r) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
