"""Q13.xx / RQ-h4-004 -- How far does each clone diverge from the
template it was started from, measured in files not shared? Same data as
RQ-h6-004 (new-surface share), read as a divergence measure instead of a
"new product" measure -- same number, opposite framing.
"""
RQ_ID = "RQ-h4-004"
QUESTION = "How far does each clone diverge from the template it was started from?"


def answer(con):
    from questions.RQ_h6_004 import answer as base_answer
    return base_answer(con)


if __name__ == "__main__":
    print(*answer(None), sep="\n")
