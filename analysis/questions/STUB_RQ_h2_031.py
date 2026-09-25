"""Q17 / RQ-h2-031 -- Which of the factory's efficiency metrics would transfer unchanged to a different factory, and which are worth re-measuring as a longitudinal baseline?

Not code-answerable: method='human', status='deferred', defer_reason='later'.
Cross-repo feature cost attribution is covered in S15; transfer needs a second factory.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h2-031"
QUESTION = "Which of the factory's efficiency metrics would transfer unchanged to a different factory, and which are worth re-measuring as a longitudinal baseline?"


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'deferred',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
