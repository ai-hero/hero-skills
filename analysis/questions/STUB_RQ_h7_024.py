"""Q2 / RQ-h7-024 -- When the study credits a process change with an outcome, is the evidence causal or only correlational?

Not code-answerable: method='human', status='now'.
Every intervention claim needs a pre/post window and a stated mechanism. Separating general findings from this factory's specifics goes to generalizability.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h7-024"
QUESTION = 'When the study credits a process change with an outcome, is the evidence causal or only correlational?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'now',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
