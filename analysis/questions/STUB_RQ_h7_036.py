"""Q18 / RQ-h7-036 -- When and why did the owner decide the fleet needed a shared control register?

Not code-answerable: method='human', status='now'.
Data trigger: the register's first commit and the drift that preceded it.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h7-036"
QUESTION = 'When and why did the owner decide the fleet needed a shared control register?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'now',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
