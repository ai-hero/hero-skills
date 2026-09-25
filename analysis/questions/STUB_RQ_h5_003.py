"""Q14 / RQ-h5-003 -- Of exceptions granted against the control register, what share are resolved by their stated deadline versus extended?

Not code-answerable: method='sql', status='deferred', defer_reason='not-recorded'.
Compliance is soft today, so deadlines don't bind; this is a forward question.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h5-003"
QUESTION = 'Of exceptions granted against the control register, what share are resolved by their stated deadline versus extended?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'sql', "status": 'deferred',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
