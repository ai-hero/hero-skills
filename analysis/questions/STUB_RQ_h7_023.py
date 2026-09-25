"""Q20 / RQ-h7-023 -- Which findings can a factory compute from a stock harness install and its own repo history, and which need new instrumentation?

Not code-answerable: method='human', status='now'.
Tells another factory what it can reuse cheaply.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h7-023"
QUESTION = 'Which findings can a factory compute from a stock harness install and its own repo history, and which need new instrumentation?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'now',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
