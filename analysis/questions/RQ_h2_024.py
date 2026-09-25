"""Q16.xx / RQ-h2-024 -- What is the distribution of time between a defect
being introduced and being found? Same D5 data as RQ-h3-008; this file
exists at a different chapter, not a different number.
"""
RQ_ID = "RQ-h2-024"
QUESTION = "What is the distribution of time between a defect being introduced and being found?"


def answer(con):
    from questions.RQ_h3_008 import answer as base_answer
    return base_answer(con)


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
