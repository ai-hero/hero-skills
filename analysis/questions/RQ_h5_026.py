"""Q14.xx / RQ-h5-026 -- When a repo's prose about itself goes false
relative to the code, how long does that state persist before it's
caught? Same limitation as NEW-C07-B: D2 drift is current-state only, no
found/fixed timestamps exist to measure a persistence duration.
"""
RQ_ID = "RQ-h5-026"
QUESTION = "When a repo's prose about itself goes false relative to the code, how long does that persist before it's caught?"


def answer(con=None):
    return [{"answerable_by_code": False,
             "reason": "detectors/d2_drift.py is current-state only, no found/fixed timestamps to measure persistence"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
