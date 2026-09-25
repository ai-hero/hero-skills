"""Q16 / RQ-h2-016 -- How much of the factory's cost and coordination behavior comes from having one operator rather than a team?

Not code-answerable: method='deferred', status='deferred', defer_reason='team'.
There is one operator; team effects cannot be observed here.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h2-016"
QUESTION = "How much of the factory's cost and coordination behavior comes from having one operator rather than a team?"


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'deferred', "status": 'deferred',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
