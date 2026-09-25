"""Q20 / RQ-h7-017 -- For each finding that depends on this fleet's conventions, what would another factory need in place to compute it?

Not code-answerable: method='human', status='now'.
Lists the fleet-specific artifacts each finding relies on.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h7-017"
QUESTION = "For each finding that depends on this fleet's conventions, what would another factory need in place to compute it?"


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'now',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
