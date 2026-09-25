"""Q18 / RQ-h7-035 -- When did spend become granular enough to shape the owner's decisions?

Not code-answerable: method='human', status='now'.
Data trigger: the first cost memory and the spend-per-week curve.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h7-035"
QUESTION = "When did spend become granular enough to shape the owner's decisions?"


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'now',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
