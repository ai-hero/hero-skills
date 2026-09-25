"""Q18 / RQ-h7-034 -- What incident prompted each new control on the automated judge and human approval gate?

Not code-answerable: method='human', status='now'.
Data trigger: for each control, the failed CI run or follow-up fix in the week before it was added (D5, D8).

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h7-034"
QUESTION = 'What incident prompted each new control on the automated judge and human approval gate?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'now',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
