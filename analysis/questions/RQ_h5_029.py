"""Q14.xx / RQ-h5-029 -- When the same fact is written in more than one
file or repo, how often does an agent update only one copy? Same headings-
disagreeing signal as RQ-h4-007/NEW-C07-C, reframed as an update-lag
question -- current-state disagreement count is answerable, "an agent
updated only one copy" (a specific edit event) is not, without per-commit
attribution to which copies changed together.
"""
RQ_ID = "RQ-h5-029"
QUESTION = "When the same fact is written in more than one file or repo, how often does an agent update only one copy?"


def answer(con):
    from questions.RQ_h4_007 import answer as base_answer
    rows = base_answer(con)[0]
    total = rows["headings_appearing_in_multiple_repos"]
    agree = rows["with_identical_text_everywhere"]
    return [{"shared_facts": total, "currently_in_sync_everywhere": agree,
             "currently_out_of_sync_somewhere": total - agree,
             "note": "current-state only -- can't attribute a specific edit to 'updated only one copy'"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
