"""Q13.xx / NEW-C07-J -- Has a bad change to a moving shared reference
ever broken a consumer, and how was it caught? Reuses RQ-h3-034's spoof/
subvert-shaped judge-testing finding as the closest recorded incident,
plus checks D8 for a CI catch on the same theme (auto-approve).
"""
RQ_ID = "NEW-C07-J"
QUESTION = "Has a bad change to a moving shared reference ever broken a consumer, and how was it caught?"


def answer(con):
    from questions.RQ_h3_034 import answer as base_answer
    return base_answer(con)


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
