"""Q10.xx / RQ-h6-028 -- After skills are renamed, how long does the owner
keep typing the old names? old_path (skill_versions) gives the old folder
slug per rename event; this counts prompts mentioning that slug after the
rename date, and how many days after the rename the last such mention was.
A slug that's also an English word (e.g. a short old name) could false-
positive against unrelated prompt text -- only slugs with a hyphen are
checked, to keep the match reasonably specific.
"""
import re

RQ_ID = "RQ-h6-028"
QUESTION = "After skills are renamed, how long does the owner keep typing the old names?"

RENAME_SQL = "SELECT skill AS new_skill, old_path, day FROM knowledge.skill_versions WHERE change_type = 'rename' OR old_path IS NOT NULL"


def old_slug(old_path):
    m = re.match(r"skills/([^/]+)/SKILL\.md", old_path or "")
    return m.group(1) if m and "-" in m.group(1) else None


def answer(con):
    renames = con.execute(RENAME_SQL).fetchall()
    out = []
    for r in renames:
        slug = old_slug(r["old_path"])
        if not slug:
            continue
        rows = con.execute(
            "SELECT MAX(day) AS last_day, COUNT(*) AS mentions FROM harness.prompts "
            "WHERE text_redacted LIKE ? AND day > ?",
            (f"%{slug}%", r["day"]),
        ).fetchone()
        if rows["mentions"]:
            import datetime as dt
            lag_days = (dt.date.fromisoformat(rows["last_day"]) - dt.date.fromisoformat(r["day"])).days
            # a slug that's also a substring of an unrelated, very common term
            # ("hero-skill" inside "hero-skills", the repo's own old name)
            # produces an implausibly high count -- flagged, not silently trusted.
            suspect = rows["mentions"] > 50
            out.append({"new_skill": r["new_skill"], "old_slug": slug, "renamed_on": r["day"],
                        "mentions_after_rename": rows["mentions"], "days_until_last_old_mention": lag_days,
                        "likely_substring_false_positive": suspect})
    return sorted(out, key=lambda x: -x["days_until_last_old_mention"])


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
