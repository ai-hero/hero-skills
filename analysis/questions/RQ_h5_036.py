"""Q7.xx / RQ-h5-036 -- When process instructions are restructured to load
detail on demand (a skill split into SKILL.md + reference files), does the
main instruction size shrink even as total content grows?
Proxy: skill_versions bytes per skill over time -- a restructure shows as a
size drop for an existing skill slug that isn't a rename (old_path is
null) on that commit.
"""
RQ_ID = "RQ-h5-036"
QUESTION = "When process instructions are restructured to load detail on demand, does the main file shrink even as total content grows?"


def answer(con):
    rows = con.execute(
        "SELECT skill, day, bytes FROM knowledge.skill_versions "
        "WHERE old_path IS NULL AND change_type != 'remove' ORDER BY skill, day"
    ).fetchall()
    by_skill = {}
    for r in rows:
        by_skill.setdefault(r["skill"], []).append((r["day"], r["bytes"]))

    shrinks = []
    for skill, versions in by_skill.items():
        for (d1, b1), (d2, b2) in zip(versions, versions[1:]):
            # bytes=0 shows up on some change_type='modify' rows too (not just
            # 'remove') -- a real ingest quirk, not a 0-byte SKILL.md -- so a
            # drop to exactly 0 is excluded as noise rather than a restructure.
            if b2 != 0 and b2 < b1 * 0.7:
                shrinks.append({"skill": skill, "from_day": d1, "to_day": d2, "bytes_before": b1, "bytes_after": b2})
    return shrinks[:30] if shrinks else [{"note": "no skill shows a >=30% single-step byte drop"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
