"""Q18 / RQ-h7-042 -- What surprised the owner most about how the factory developed, and what would they tell someone starting one?

Not code-answerable: method='human', status='now'.
Retrospective testimony for the discussion chapter.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h7-042"
QUESTION = 'What surprised the owner most about how the factory developed, and what would they tell someone starting one?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'now',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
