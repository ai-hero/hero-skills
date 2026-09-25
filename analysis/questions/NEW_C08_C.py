"""Q14.xx / NEW-C08-C -- How long does a repo failing a control take to
catch up to the template or to a passing sibling? No per-control fail-to-
pass event history exists (check_results is a single snapshot per sync,
not a continuous timeline for one control in one repo) -- not answerable
without re-syncing the register at multiple points in time.
"""
RQ_ID = "NEW-C08-C"
QUESTION = "How long does a repo failing a control take to catch up to the template or a passing sibling?"


def answer(con=None):
    return [{"answerable_by_code": False,
             "reason": "check_results is a snapshot per sync, not a per-control fail-to-pass timeline"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
