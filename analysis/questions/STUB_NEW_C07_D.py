"""Q13 / NEW-C07-D -- Does flagging a cross-repo message as non-urgent change whether it ever gets an answer?

Not code-answerable: method='sql', status='deferred', defer_reason='not-recorded'.
Split from RQ 07.08. Too few messages and no urgency field recorded to answer now.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "NEW-C07-D"
QUESTION = 'Does flagging a cross-repo message as non-urgent change whether it ever gets an answer?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'sql', "status": 'deferred',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
