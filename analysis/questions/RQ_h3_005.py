"""Q11.xx / RQ-h3-005 -- How often is the same defect or fix independently
rediscovered and re-implemented in more than one repo? Same D7 "look like
separate builds" count as RQ-h6-002 (clusters with no template involved),
reframed as rediscovery.
"""
RQ_ID = "RQ-h3-005"
QUESTION = "How often is the same defect or fix independently rediscovered and re-implemented in more than one repo?"


def answer(con):
    from questions.RQ_h6_002 import answer as base_answer
    rows = base_answer(con)
    return [rows[0]] if rows and "summary" in rows[0] else rows


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
