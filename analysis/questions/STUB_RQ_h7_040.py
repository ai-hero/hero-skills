"""Q18 / RQ-h7-040 -- Looking back, would the owner build the template and process plugin first, or let products invent and consolidate upward?

Not code-answerable: method='human', status='now'.
The central design choice of a factory: top-down platform or bottom-up extraction.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h7-040"
QUESTION = 'Looking back, would the owner build the template and process plugin first, or let products invent and consolidate upward?'


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'human', "status": 'now',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
