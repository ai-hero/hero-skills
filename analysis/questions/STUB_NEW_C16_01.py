"""Q17 / NEW-C16-01 -- Does the factory define its unit of shipped output (change set, merged PR, closed work item) and record enough per unit to compute cost, time and defects for it?

Not code-answerable: method='human', status='now'.
Efficiency ratios need a numerator; the owner chose the change set as the default unit, rolling up to PR, item, goal, repo and fleet.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "NEW-C16-01"
QUESTION = 'Does the factory define its unit of shipped output (change set, merged PR, closed work item) and record enough per unit to compute cost, time and defects for it?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'now',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
