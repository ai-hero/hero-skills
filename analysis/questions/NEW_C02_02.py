"""Q9.xx / NEW-C02-02 -- How many harness outages (session limits, provider
errors) did the factory hit, and how long did each last? Reuses RQ-h6-053's
own merged-stall computation (same limit_events source) rather than
recomputing it -- see that file for the merge-window and stall-duration
methodology and its caveats.
"""
RQ_ID = "NEW-C02-02"
QUESTION = "How many harness outages did the factory hit, and how long did each last?"


def answer(con):
    from questions.RQ_h6_053 import answer as rq_h6_053_answer
    weekly = rq_h6_053_answer(con)
    total_stalls = sum(r["stalls"] for r in weekly)
    total_minutes = sum(r["total_stall_minutes"] for r in weekly)
    return [{"total_outages": total_stalls, "total_outage_hours": round(total_minutes / 60, 1)}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
