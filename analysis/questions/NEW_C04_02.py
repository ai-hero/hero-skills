"""Q3.xx / NEW-C04-02 -- How many outages (provider limits, harness down)
did the factory hit, and how much working time did each cost? Same D6
merged-stall data as RQ-h6-053/NEW-C02-02, reframed with working-time-lost
instead of raw duration.
"""
RQ_ID = "NEW-C04-02"
QUESTION = "How many outages did the factory hit, and how much working time did each cost?"


def answer(con):
    from questions.NEW_C02_02 import answer as base_answer
    return base_answer(con)


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
