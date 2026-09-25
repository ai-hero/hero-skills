"""Q5.xx / RQ-h6-027 -- Does the size of the process plugin's instructions
and scripts level off as the factory matures?

Total size = sum of each skill's most-recent known byte count as of each
month end (a skill not touched that month keeps its last known size; a
removed skill drops out). "Levels off" is for the reader to judge from the
month-over-month delta column, not asserted here.
"""
RQ_ID = "RQ-h6-027"
QUESTION = "Does the size of the process plugin's instructions and scripts level off as the factory matures?"

SQL = "SELECT skill, month, bytes, change_type FROM knowledge.skill_versions ORDER BY month"


def answer(con):
    rows = con.execute(SQL).fetchall()
    months = sorted({r["month"] for r in rows})
    sizes = {}
    out = []
    prev_total = None
    for month in months:
        for r in rows:
            if r["month"] != month:
                continue
            if r["change_type"] == "remove":
                sizes.pop(r["skill"], None)
            else:
                sizes[r["skill"]] = r["bytes"] or 0
        total = sum(sizes.values())
        out.append({
            "month": month, "total_bytes": total, "skills": len(sizes),
            "delta_bytes": total - prev_total if prev_total is not None else None,
        })
        prev_total = total
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
