"""Q14 / RQ-h5-018 -- Where a rule says to treat a gap as an incident, has that gap ever happened, and was it handled as one?

Not code-answerable: method='human', status='deferred', defer_reason='not-recorded'.
No incident records exist; moved to security. The shared-credential half is also S13.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h5-018"
QUESTION = 'Where a rule says to treat a gap as an incident, has that gap ever happened, and was it handled as one?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'deferred',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
