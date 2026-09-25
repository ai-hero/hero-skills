"""Q15.xx / RQ-h5-008 -- What triggered each control's creation: an
incident, a scheduled audit, or a proactive design decision? sql half:
the same keyword proxy as NEW-C08-02, split into a finer trigger guess.
Genuinely determining the trigger needs the control's own creation
context (a linked ticket or commit message), not just its title text.
"""
RQ_ID = "RQ-h5-008"
QUESTION = "What triggered each control's creation: an incident, a scheduled audit, or a proactive design decision?"

_INCIDENT_KW = ["incident", "postmortem", "cve", "regression", "outage", "vulnerab"]
_AUDIT_KW = ["audit", "sweep", "compliance review", "quarterly"]


def answer(con):
    rows = con.execute("SELECT control_id, title, raw_json, created_ts FROM knowledge.controls").fetchall()
    buckets = {"incident_by_keyword": 0, "audit_by_keyword": 0, "unclassified": 0}
    for r in rows:
        text = ((r["title"] or "") + " " + (r["raw_json"] or "")).lower()
        if any(kw in text for kw in _INCIDENT_KW):
            buckets["incident_by_keyword"] += 1
        elif any(kw in text for kw in _AUDIT_KW):
            buckets["audit_by_keyword"] += 1
        else:
            buckets["unclassified"] += 1
    return [{"total_controls": len(rows), **buckets,
             "answerable_by_code": "partial",
             "reason": "buckets above are a keyword proxy on the control's own title/definition, not "
                       "a verified trigger; most controls will fall into 'unclassified' since a "
                       "proactive design decision leaves no incident/audit keyword to match on"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
