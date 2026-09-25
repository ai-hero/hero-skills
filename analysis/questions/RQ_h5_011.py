"""Q14.xx / RQ-h5-011 -- From a control violation existing to it being
detected, what is the typical lag? Same snapshot-only gap as NEW-C08-C --
check_results has no fail-to-pass timeline for a given control in a given
repo, only point-in-time syncs.
"""
RQ_ID = "RQ-h5-011"
QUESTION = "From a control violation existing to it being detected, what is the typical lag?"


def answer(con=None):
    return [{"answerable_by_code": False,
             "reason": "check_results is a snapshot per sync, not a violation-detection timeline"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
