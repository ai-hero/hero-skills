"""Q9.xx / RQ-h3-004 -- For each automated reviewer persona (code,
security, completeness, comments), how often does another persona (or
the human) catch what it missed? Alias to NEW-C05-03's data.
"""
RQ_ID = "RQ-h3-004"
QUESTION = "For each automated reviewer persona, how often does another persona or the human catch what it missed?"


def answer(con):
    from questions.NEW_C05_03 import answer as base_answer
    return base_answer(con)


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
