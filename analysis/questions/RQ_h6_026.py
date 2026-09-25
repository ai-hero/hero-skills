"""Q5.xx / RQ-h6-026 -- How has the number of skills in the process plugin
changed over time?

skill_versions has one row per commit that touched a skill (add/modify/
remove via change_type), so the running skill count at month end is: every
skill first added on or before that month, minus every one removed on or
before it. A rename shows as a remove of the old name plus an add of the
new one (change_type on both rows), which briefly double-counts a renamed
skill within the same month -- real skills-in-repo count at month END is
still correct since both rows are resolved by then.
"""
RQ_ID = "RQ-h6-026"
QUESTION = "How has the number of skills in the process plugin changed over time?"

SQL = "SELECT skill, month, change_type FROM knowledge.skill_versions ORDER BY month"


def answer(con):
    rows = con.execute(SQL).fetchall()
    months = sorted({r["month"] for r in rows})
    alive = set()
    out = []
    for month in months:
        for r in rows:
            if r["month"] != month:
                continue
            if r["change_type"] == "remove":
                alive.discard(r["skill"])
            else:
                alive.add(r["skill"])
        out.append({"month": month, "skills_in_repo": len(alive)})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
