"""Q16.xx / RQ-h2-026 -- What are the factory's takt time and cycle-time
distribution, and do PR-level and item-level views agree? Combines
RQ-h1-020's item lead-time distribution with RQ-h1-030's PR wall-time
distribution side by side.
"""
RQ_ID = "RQ-h2-026"
QUESTION = "What are the factory's takt time and cycle-time distributions, at the item and PR level?"


def answer(con):
    from questions.RQ_h1_020 import answer as item_answer
    from questions.RQ_h1_030 import answer as pr_answer
    return [{"item_level": item_answer(con)}, {"pr_level": pr_answer(con)}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
