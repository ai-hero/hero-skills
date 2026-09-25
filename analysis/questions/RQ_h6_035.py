"""Q17.xx / RQ-h6-035 -- Is there a standing channel for the owner's
feedback to reach skill design, and what share of that feedback lands?
sql half: prompt_kind's correction/redirect counts, as a proxy for how
much owner feedback flows at all. Whether it specifically "lands" in a
skill-design change needs matching a correction to a subsequent skill
edit, which needs a human or a purpose-built classifier this repo
doesn't have.
"""
RQ_ID = "RQ-h6-035"
QUESTION = "Is there a standing channel for the owner's feedback to reach skill design, and what share lands?"


def answer(con):
    kinds = con.execute(
        "SELECT kind, COUNT(*) AS n FROM detectors.prompt_kind GROUP BY kind ORDER BY n DESC"
    ).fetchall()
    total = sum(r["n"] for r in kinds)
    correction_share = next((r["n"] for r in kinds if r["kind"] == "correction"), 0)
    return [{"prompt_kind_distribution": {r["kind"]: r["n"] for r in kinds},
             "correction_or_redirect_share_of_all_prompts":
                 round((correction_share + next((r["n"] for r in kinds if r["kind"] == "redirect"), 0)) / total, 4)
                 if total else None},
            {"answerable_by_code": "partial",
             "reason": "the volume of correction/redirect-shaped feedback is measurable above; "
                       "whether a specific piece of feedback later shows up as a skill-design change "
                       "is not traced here"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
