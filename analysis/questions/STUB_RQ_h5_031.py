"""Q7 / RQ-h5-031 -- Has a fact kept only in the unversioned local fleet map ever needed a history it didn't have?

Not code-answerable: method='human', status='deferred', defer_reason='not-recorded'.
FLEET.md is local and unversioned by design; the cost is no audit trail.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h5-031"
QUESTION = "Has a fact kept only in the unversioned local fleet map ever needed a history it didn't have?"


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'deferred',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
