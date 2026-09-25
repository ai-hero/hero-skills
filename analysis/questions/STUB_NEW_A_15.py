"""Q20 / NEW-A-15 -- Is every research question stated in generic roles, so another factory can supply its own grounding?

Not code-answerable: method='human', status='now'.
Opens generalizability; a question in our names can't be asked of another factory.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "NEW-A-15"
QUESTION = 'Is every research question stated in generic roles, so another factory can supply its own grounding?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'now',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
