"""Q9 / RQ-h1-024 -- Does the factory set an effort or cost budget per unit of work, and when it does, how often is it exceeded?

Not code-answerable: method='deferred', status='deferred', defer_reason='not-recorded'.
Asked for other factories; ours sets no per-unit budget. Proxy available: commits or PRs per goal. Premise-wrong-at-execution goes to S12.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h1-024"
QUESTION = 'Does the factory set an effort or cost budget per unit of work, and when it does, how often is it exceeded?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'deferred', "status": 'deferred',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
