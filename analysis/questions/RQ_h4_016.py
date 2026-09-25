"""Q13.xx / RQ-h4-016 -- Does the size of a repo's design record track its
architectural complexity, or just its age and churn? Same data as
RQ-h6-005, a different chapter's framing of the same question.
"""
RQ_ID = "RQ-h4-016"
QUESTION = "Does the size of a repo's design record track its architectural complexity, or just age and churn?"


def answer(con):
    from questions.RQ_h6_005 import answer as base_answer
    return base_answer(con)


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
