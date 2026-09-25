"""Q18 / NEW-C15-02 -- When did the owner choose speed over doing something right the first time, and what did it cost in follow-up fixes?

Not code-answerable: method='human', status='now'.
Split from 15.06. Data trigger: follow-up fixes within days of merge (D5).

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "NEW-C15-02"
QUESTION = 'When did the owner choose speed over doing something right the first time, and what did it cost in follow-up fixes?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'now',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
