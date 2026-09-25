"""Q10 / RQ-h3-022 -- Does the automated PR judge catch a fabricated completion claim in a PR description as reliably as a real code defect?

Not code-answerable: method='human', status='deferred', defer_reason='not-recorded'.
The judge reads descriptions; a false description is an attack and a mistake.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h3-022"
QUESTION = 'Does the automated PR judge catch a fabricated completion claim in a PR description as reliably as a real code defect?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'deferred',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
