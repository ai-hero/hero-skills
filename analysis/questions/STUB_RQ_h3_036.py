"""Q11 / RQ-h3-036 -- What secrets or binaries are provisioned into infrastructure boot configuration without encryption or integrity checks?

Not code-answerable: method='deferred', status='deferred', defer_reason='code-deep-dive'.
Boot-time secrets are an infra exposure.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h3-036"
QUESTION = 'What secrets or binaries are provisioned into infrastructure boot configuration without encryption or integrity checks?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'deferred', "status": 'deferred',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
