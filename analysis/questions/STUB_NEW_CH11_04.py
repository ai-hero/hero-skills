"""Q20 / NEW-CH11-04 -- Where do other factories keep a human reading intermediate output, and does this factory's gate placement agree?

Not code-answerable: method='human', status='now'.
Places this factory's numbers next to what others in the field have published.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "NEW-CH11-04"
QUESTION = "Where do other factories keep a human reading intermediate output, and does this factory's gate placement agree?"


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'now',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
