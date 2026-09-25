"""Q11.xx / RQ-h3-020 -- What share of bug-fix PRs repair a defect
introduced by an earlier agent session?

The obvious D5-reversed join (does this fix-type PR's merge fall within
14 days of ANY earlier PR's followup window) is meaningless in a busy fleet:
some earlier PR's 14-day window is open nearly all the time, so a match says
nothing about causation. Not publishing that as an answer. A real answer needs the
SAME-FILE-OVERLAP join D5 already does, but keyed to a SPECIFIC earlier PR
(not "any PR in the window"), which needs re-deriving followups.py's
per-pair overlap here rather than reusing its output -- not done, to avoid
duplicating that logic with a different, unvalidated threshold.
"""
RQ_ID = "RQ-h3-020"
QUESTION = "What share of bug-fix PRs repair a defect introduced by an earlier agent session?"


def answer(con=None):
    return [{"answerable_by_code": False,
             "reason": "the obvious proxy (fix PR merged within 14d of any earlier PR's followup window) "
                       "matched nearly every PR -- too dense to mean anything; a real answer needs a specific-pair "
                       "file-overlap join, not built here"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
