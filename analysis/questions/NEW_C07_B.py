"""Q13.xx / NEW-C07-B -- When a drift between design record and code is
found in one repo, how long until it's fixed there and checked in
siblings? D2's single tracked artifact (.claude/rules/comments.md)
doesn't carry a "found" timestamp distinct from "currently drifted" (see
d2_drift.py's own docstring: current-state only, no interval) -- not
answerable at the precision asked without extending that detector to walk
history.
"""
RQ_ID = "NEW-C07-B"
QUESTION = "When a drift between design record and code is found, how long until it's fixed and checked in siblings?"


def answer(con=None):
    return [{"answerable_by_code": False,
             "reason": "detectors/d2_drift.py reports current-state drift only, no found/fixed timestamps -- "
                       "would need a git-log walk of the tracked file per repo, not built"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
