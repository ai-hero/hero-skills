"""Q16.xx / NEW-C08-02 -- What share of controls trace to a recorded bug
or incident? sql: keyword proxy on each control's title/raw_json for
incident-shaped language ("incident", "postmortem", "CVE", "regression",
"outage"), following the same honest-proxy pattern as RQ-h6-028.
"""
RQ_ID = "NEW-C08-02"
QUESTION = "What share of controls trace to a recorded bug or incident?"

_KEYWORDS = ["incident", "postmortem", "cve", "regression", "outage", "bug", "vulnerab"]


def answer(con):
    rows = con.execute("SELECT control_id, title, raw_json FROM knowledge.controls").fetchall()
    hits = []
    for r in rows:
        text = ((r["title"] or "") + " " + (r["raw_json"] or "")).lower()
        if any(kw in text for kw in _KEYWORDS):
            hits.append(r["control_id"])
    total = len(rows)
    return [{"total_controls": total, "incident_shaped_by_keyword": len(hits),
             "share": round(len(hits) / total, 4) if total else None,
             "answerable_by_code": "partial",
             "reason": "this is a keyword match on the control's own title/definition text, not a "
                       "verified trace to an actual bug ticket or incident report; a control can use "
                       "incident language without being incident-derived, and vice versa"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
