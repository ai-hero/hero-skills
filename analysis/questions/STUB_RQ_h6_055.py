"""Q3 / RQ-h6-055 -- How many local safety gates can be bypassed by running the same work in an isolated agent environment, and has that path been used?

Not code-answerable: method='human', status='deferred', defer_reason='code-deep-dive'.
Isolation could skip local hooks.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h6-055"
QUESTION = 'How many local safety gates can be bypassed by running the same work in an isolated agent environment, and has that path been used?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'deferred',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
