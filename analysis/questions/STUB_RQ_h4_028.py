"""Q8 / RQ-h4-028 -- When a design is superseded, how much of the old code or docs is actually removed?

Not code-answerable: method='deferred', status='deferred', defer_reason='code-deep-dive'.
Needs reading code for unused weight. Doc-side leftovers could be scanned later.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h4-028"
QUESTION = 'When a design is superseded, how much of the old code or docs is actually removed?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'deferred', "status": 'deferred',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
