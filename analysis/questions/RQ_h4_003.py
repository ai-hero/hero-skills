"""Q13.xx / RQ-h4-003 -- When the same fix recurs in several clones, what
share came from one upstream root versus independent invention in each?
Same D7 cluster data as RQ-h6-002.
"""
RQ_ID = "RQ-h4-003"
QUESTION = "When the same fix recurs in several clones, what share came from one upstream root?"


def answer(con):
    from questions.RQ_h6_002 import answer as base_answer
    rows = base_answer(con)
    return [rows[0]] if rows and "summary" in rows[0] else rows


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
