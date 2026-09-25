"""Q16.xx / RQ-h2-005 -- When a capability is needed by more than one
clone, what does it cost to build it separately in each versus sharing it
once? Same shape as RQ-h2-004, for the "capability" (feature-shaped, not
defect-shaped) clusters -- D7 doesn't distinguish feature vs defect
clusters, so this is the same number under a different framing.
"""
RQ_ID = "RQ-h2-005"
QUESTION = "When a capability is needed by more than one clone, what does it cost to build it separately versus once?"


def answer(con):
    from questions.RQ_h2_004 import answer as base_answer
    return base_answer(con)


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
