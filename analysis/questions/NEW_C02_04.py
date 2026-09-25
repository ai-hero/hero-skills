"""Q9.xx / NEW-C02-04 -- What share of lead time is waiting for the human,
versus working, CI, and limit stalls? Same D6 breakdown as RQ-h7-003,
reported under this question's own framing (session-time share, not item
lead-time share -- item-level lead time and session-level elapsed time are
different clocks; see RQ-h1-020 for the item-level one).
"""
RQ_ID = "NEW-C02-04"
QUESTION = "What share of session time is waiting for the human, versus working, versus limited?"


def answer(con):
    from questions.RQ_h7_003 import answer as base_answer
    return base_answer(con)


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
