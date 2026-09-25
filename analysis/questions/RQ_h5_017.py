"""Q15.xx / RQ-h5-017 -- How many work items need a human to verify
because the agent lacks credentials or access, and how long does that
add? Same keyword-proxy data as NEW-C02-03, reframed around hours-open
as the added-time signal.
"""
RQ_ID = "RQ-h5-017"
QUESTION = "How many work items need a human to verify because the agent lacks credentials or access, and how long does that add?"


def answer(con):
    from questions.NEW_C02_03 import answer as base_answer, _KEYWORDS
    rows = con.execute(
        "SELECT repo, number, title, body_redacted, hours_open FROM github.prs WHERE body_redacted IS NOT NULL"
    ).fetchall()
    hits = [dict(r) for r in rows if any(
        kw in ((r["title"] or "") + " " + (r["body_redacted"] or "")).lower() for kw in _KEYWORDS
    )]
    hours = [h["hours_open"] for h in hits if h["hours_open"] is not None]
    return [{"candidate_access_blocked_items": len(hits),
             "avg_hours_open_for_these": round(sum(hours) / len(hours), 1) if hours else None,
             "avg_hours_open_overall": round(
                 sum(r["hours_open"] for r in rows if r["hours_open"] is not None) /
                 max(1, len([r for r in rows if r["hours_open"] is not None])), 1),
             "answerable_by_code": "partial",
             "reason": "same keyword-proxy caveat as NEW-C02-03: candidate count and time-open "
                       "comparison, not a verified access-block classification"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
