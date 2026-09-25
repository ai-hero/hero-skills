"""Q13.xx / NEW-C07-A -- When a recurring fix was adopted from upstream,
how long did it take from the upstream commit to the local adoption? Same
D3 lag distribution as RQ-h6-014/RQ-h4-010, scoped to the process plugin
and template as upstream (the two "process" upstreams, vs design-system's
product-surface propagation).
"""
RQ_ID = "NEW-C07-A"
QUESTION = "When a recurring fix was adopted from upstream, how long did it take?"


def answer(con):
    from questions.RQ_h6_003 import answer as base_answer
    return base_answer(con)


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
