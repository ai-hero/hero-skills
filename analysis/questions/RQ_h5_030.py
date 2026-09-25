"""Q15.xx / RQ-h5-030 -- Can a fresh agent rely on the design record's
decision log alone to avoid reopening a past decision? Not computable
from ingested data: it requires simulating a fresh agent's read of a
DESIGN.md decision log and checking whether a later change actually
reopened a logged decision, which is a human (or a much larger agentic)
evaluation, not a query.
"""
RQ_ID = "RQ-h5-030"
QUESTION = "Can a fresh agent rely on the design record's decision log alone to avoid reopening a past decision?"


def answer(con):
    return [{"answerable_by_code": False,
             "reason": "would need to simulate a fresh agent reading each repo's design-decision "
                       "log and check later history for reopened decisions; not a query over the "
                       "ingested tables"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
