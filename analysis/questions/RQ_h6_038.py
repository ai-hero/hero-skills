"""Q10.xx / RQ-h6-038 -- When two skills are merged into one, is the
merged skill smaller and cheaper to run than the sum of the originals?
A merge shows as >=2 distinct old_path skill-slugs collapsing into the same
new `skill` value. Reports the merged skill's current size only -- the
originals' pre-merge sizes aren't reliably recoverable from skill_versions
once their rows are superseded by the rename, so this can't yet compute
"smaller than the sum," only list the merges and their resulting size.
"""
import re

RQ_ID = "RQ-h6-038"
QUESTION = "When two skills are merged into one, is the merged skill smaller than the sum of the originals?"


def old_slug(old_path):
    m = re.match(r"skills/([^/]+)/SKILL\.md", old_path or "")
    return m.group(1) if m else None


def answer(con):
    rows = con.execute(
        "SELECT skill, old_path, day, bytes FROM knowledge.skill_versions WHERE old_path IS NOT NULL ORDER BY day"
    ).fetchall()
    by_new = {}
    for r in rows:
        slug = old_slug(r["old_path"])
        if slug:
            by_new.setdefault(r["skill"], set()).add(slug)

    merges = {new: olds for new, olds in by_new.items() if len(olds) >= 2}
    out = []
    for new_skill, olds in merges.items():
        latest = con.execute(
            "SELECT bytes FROM knowledge.skill_versions WHERE skill = ? ORDER BY day DESC LIMIT 1", (new_skill,)
        ).fetchone()
        out.append({"merged_skill": new_skill, "absorbed_old_slugs": sorted(olds),
                    "merged_skill_current_bytes": latest[0] if latest else None})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
