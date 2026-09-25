"""Q16.xx / RQ-h2-007 -- What share of CI minutes goes to runs that cannot
change an outcome? Same scoped answer as RQ-cicd-001, at a different
chapter.
"""
RQ_ID = "RQ-h2-007"
QUESTION = "What share of CI minutes goes to runs that cannot change an outcome?"


def answer(con):
    from questions.RQ_cicd_001 import answer as base_answer
    return base_answer(con)


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
