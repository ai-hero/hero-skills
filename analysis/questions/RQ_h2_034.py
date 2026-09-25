"""Q17.xx / RQ-h2-034 -- What is the size distribution of merged changes
in change sets, and is it stable over time? D1-backed, reusing NEW-A-02's
distribution plus a per-month view.
"""
RQ_ID = "RQ-h2-034"
QUESTION = "What is the size distribution of merged changes in change sets, and is it stable over time?"


def answer(con):
    from questions.NEW_A_02 import answer as base_answer
    return base_answer(con)


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
