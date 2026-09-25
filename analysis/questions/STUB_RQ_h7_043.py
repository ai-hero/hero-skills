"""Q18 / RQ-h7-043 -- When did agent memory become something the factory depended on rather than documentation?

Not code-answerable: method='human', status='now'.
Data trigger: the week memory counts and 'why' lines jump. The owner supplies what changed.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h7-043"
QUESTION = 'When did agent memory become something the factory depended on rather than documentation?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'now',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
