"""Q16.xx / RQ-h2-022 -- What stops the factory's flow (human queues, CI
blocking all merges, harness limits)? D6's session_time_segments totals,
already the breakdown of what non-working time is spent on.
"""
RQ_ID = "RQ-h2-022"
QUESTION = "What stops the factory's flow: human queues, harness limits, or away time?"


def answer(con):
    from questions.RQ_h7_003 import answer as base_answer
    return base_answer(con)


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
