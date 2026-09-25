"""Q10.xx / RQ-h6-034 -- Are skills marked human-only ever invoked by an
agent? No "human-only" marker is ingested anywhere (no SKILL.md frontmatter
field captured for it, no such column in skill_versions/skills) -- not
answerable without extending ingest/knowledge.py to read that field, if one
even exists in the source files.
"""
RQ_ID = "RQ-h6-034"
QUESTION = "Are skills marked human-only ever invoked by an agent?"


def answer(con=None):
    return [{"answerable_by_code": False, "reason": "no human-only marker is captured by any ingest script"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
