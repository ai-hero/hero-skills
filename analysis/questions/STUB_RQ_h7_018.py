"""Q20 / RQ-h7-018 -- Which of this factory's verification practices are transferable rules any factory could adopt?

Not code-answerable: method='human', status='now'.
Candidate rules: see a gate fail before trusting it; group visual defects by region; guard a registry against consuming itself.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h7-018"
QUESTION = "Which of this factory's verification practices are transferable rules any factory could adopt?"


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'now',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
