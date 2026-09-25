"""Q6 / RQ-h6-006 -- How consistently do clones take UI components from the shared design-system registry rather than writing their own?

Not code-answerable: method='deferred', status='deferred', defer_reason='code-deep-dive'.
Hand-rolled components drift from the design system.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h6-006"
QUESTION = 'How consistently do clones take UI components from the shared design-system registry rather than writing their own?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'deferred', "status": 'deferred',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
