"""Q9.xx / RQ-h3-002 -- What share of agent mistakes does the agent
record itself, which mistake types recur most, and is that share
rising or falling? Same proxy data as NEW-C05-02; alias.
"""
RQ_ID = "RQ-h3-002"
QUESTION = "What share of agent mistakes does the agent record itself, which types recur most, and is that share rising or falling?"


def answer(con):
    from questions.NEW_C05_02 import answer as base_answer
    return base_answer(con)


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
