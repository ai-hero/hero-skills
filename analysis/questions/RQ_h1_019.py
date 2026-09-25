"""Q9.xx / RQ-h1-019 -- How does the work-item store schema differ across
repos, and how much does that break fleet-wide rollups? Same schema-era
data as RQ-h5-033/RQ-h7-016, reframed as a rollup-impact question: how
many items are silently excluded if a query only reads new-era fields.
"""
RQ_ID = "RQ-h1-019"
QUESTION = "How does the work-item store schema differ across repos, and how much does that break fleet-wide rollups?"


def answer(con):
    rows = con.execute("SELECT schema_era, COUNT(*) AS n FROM plans.plan_items GROUP BY schema_era").fetchall()
    total = sum(r["n"] for r in rows)
    old = sum(r["n"] for r in rows if r["schema_era"] == "old")
    return [{"total_items": total, "old_schema_items": old,
             "excluded_share_if_a_rollup_reads_new_era_fields_only": round(old / total, 3) if total else None}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
