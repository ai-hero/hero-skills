"""Q11 / RQ-h3-035 -- What is the largest blast radius held by a single infrastructure credential, and has it shrunk since it was identified?

Not code-answerable: method='deferred', status='deferred', defer_reason='code-deep-dive'.
Credential scope is a fleet risk, but measuring it needs reading infrastructure config and live grants.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h3-035"
QUESTION = 'What is the largest blast radius held by a single infrastructure credential, and has it shrunk since it was identified?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'deferred', "status": 'deferred',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
