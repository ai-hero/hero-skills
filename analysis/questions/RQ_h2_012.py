"""Q16.xx / RQ-h2-012 -- When work in one repo is blocked on a fix
upstream, how long passes from the block to the fix landing and being
picked up? D3 propagation lag directly (upstream commit to downstream
arrival IS this measurement).
"""
RQ_ID = "RQ-h2-012"
QUESTION = "When work in one repo is blocked on a fix upstream, how long passes until it's picked up?"


def answer(con):
    from questions.RQ_h6_014 import answer as base_answer
    return base_answer(con)


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
