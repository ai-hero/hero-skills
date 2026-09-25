"""Q20 / NEW-PF-11 -- For each factory we compare against, has it published a figure defined the same way as ours?

Not code-answerable: method='human', status='now'.
A comparison is only fair when both sides define the number the same way.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "NEW-PF-11"
QUESTION = 'For each factory we compare against, has it published a figure defined the same way as ours?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'now',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
