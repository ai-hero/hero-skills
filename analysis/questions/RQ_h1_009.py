"""Q12.xx / RQ-h1-009 -- When more than one clone needs the same fix, how
often is it fixed first in the template and inherited, versus fixed
independently in each? Same D7 cluster data as RQ-h6-002/NEW-C07-02, at a
different chapter.
"""
RQ_ID = "RQ-h1-009"
QUESTION = "When more than one clone needs the same fix, is it fixed first in the template, or independently?"


def answer(con):
    from questions.RQ_h6_002 import answer as base_answer
    rows = base_answer(con)
    return [rows[0]] if rows and "summary" in rows[0] else rows


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
