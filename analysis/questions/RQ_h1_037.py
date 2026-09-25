"""Q9.xx / RQ-h1-037 -- How many agent sessions (a fresh start or a
context clear) does it take to get one work item done?
D9-backed, same low-coverage caveat as RQ-h6-042 -- this file exists
because the bank asks it at a different chapter, not because the answer
differs; see RQ-h6-042 for the number and its coverage caveat.
"""
RQ_ID = "RQ-h1-037"
QUESTION = "How many agent sessions does it take to get one work item done?"


def answer(con):
    from questions.RQ_h6_042 import answer as base_answer
    return base_answer(con)


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
