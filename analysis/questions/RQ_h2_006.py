"""Q16.xx / RQ-h2-006 -- How does the cost of agent review scale with a
change's risk or reversibility? No risk/reversibility label exists on a
PR or review (plan_items.one_way_door exists but isn't joined to any
specific PR) -- proxy: review count vs PR size (lines changed) as a risk
stand-in.
"""
RQ_ID = "RQ-h2-006"
QUESTION = "How does the cost of agent review scale with a change's size (as a risk proxy)?"


def answer(con):
    rows = con.execute(
        "SELECT review_count, additions, deletions FROM github.prs WHERE review_count IS NOT NULL"
    ).fetchall()
    buckets = {"small (<50 lines)": [], "medium (50-500)": [], "large (500+)": []}
    for r in rows:
        size = (r["additions"] or 0) + (r["deletions"] or 0)
        key = "small (<50 lines)" if size < 50 else "medium (50-500)" if size < 500 else "large (500+)"
        buckets[key].append(r["review_count"])
    return [{"bucket": k, "prs": len(v), "avg_reviews": round(sum(v) / len(v), 2) if v else None}
            for k, v in buckets.items()]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
