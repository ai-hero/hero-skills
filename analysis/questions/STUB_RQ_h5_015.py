"""Q14 / RQ-h5-015 -- Does each repo's stated enforcement for required checks (e.g. branch protection) match what the platform actually shows?

Not code-answerable: method='sql', status='deferred', defer_reason='not-recorded'.
Documentation claims vs live platform config; needs a live API read not in the ingest.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h5-015"
QUESTION = "Does each repo's stated enforcement for required checks (e.g. branch protection) match what the platform actually shows?"


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'sql', "status": 'deferred',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
