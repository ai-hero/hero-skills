"""Q13.xx / RQ-h4-010 -- When one change is swept to every repo in the
fleet, how long until it reaches all of them? Same D3 lag distribution as
RQ-h6-014, at a different chapter.
"""
RQ_ID = "RQ-h4-010"
QUESTION = "When one change is swept to every repo in the fleet, how long until it reaches all of them?"


def answer(con):
    from questions.RQ_h6_014 import answer as base_answer
    return base_answer(con)


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
