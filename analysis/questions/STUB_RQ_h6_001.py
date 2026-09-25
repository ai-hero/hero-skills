"""Q5 / RQ-h6-001 -- For each clone, how many planned features are complete and usable end to end, versus only marked done?

Not code-answerable: method='deferred', status='deferred', defer_reason='code-deep-dive'.
Done in the store and done for a user are different; the gap is overstated completion.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h6-001"
QUESTION = 'For each clone, how many planned features are complete and usable end to end, versus only marked done?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'deferred', "status": 'deferred',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
