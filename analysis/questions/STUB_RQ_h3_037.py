"""Q11 / RQ-h3-037 -- Does a live check of each environment's network exposure match what the documentation claims?

Not code-answerable: method='deferred', status='deferred', defer_reason='not-recorded'.
A claim no one checks live is a claim on faith.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h3-037"
QUESTION = "Does a live check of each environment's network exposure match what the documentation claims?"


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'deferred', "status": 'deferred',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
