"""Q18 / RQ-h7-039 -- Which single incident most changed how the factory runs?

Not code-answerable: method='human', status='now'.
Retrospective anchor; data offers candidates (reverts, outages, the rename breakage).

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h7-039"
QUESTION = 'Which single incident most changed how the factory runs?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'now',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
