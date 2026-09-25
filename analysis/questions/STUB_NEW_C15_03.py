"""Q18 / NEW-C15-03 -- Which of the owner's own standing rules was hardest to enforce, and why?

Not code-answerable: method='human', status='now'.
Split from 15.02. Data trigger: controls with the longest failing streaks.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "NEW-C15-03"
QUESTION = "Which of the owner's own standing rules was hardest to enforce, and why?"


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'now',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
