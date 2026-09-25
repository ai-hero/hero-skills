"""Q19.xx / RQ-h7-027 -- What is the smallest part of the control
register another factory could reuse, and what signals show it
transfers cleanly? sql half: controls/checks that reference nothing
fleet-specific (no repo name, no fleet-specific path) in their own
text, as a candidate portable subset. Confirming it actually transfers
to another factory needs that factory to try it -- a human/organizational
step, not a query.
"""
RQ_ID = "RQ-h7-027"
QUESTION = "What is the smallest part of the control register another factory could reuse, and what signals show it transfers cleanly?"


def answer(con):
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ingest.fleet import ALL_REPOS
    controls = con.execute("SELECT control_id, title, raw_json, repo FROM knowledge.controls").fetchall()
    fleet_specific_terms = [r.lower() for r in ALL_REPOS]
    portable = []
    for r in controls:
        text = ((r["title"] or "") + " " + (r["raw_json"] or "")).lower()
        if not any(term in text for term in fleet_specific_terms):
            portable.append(r["control_id"])
    return [{"total_controls": len(controls), "no_fleet_repo_name_in_text": len(portable),
             "candidate_portable_control_ids": portable},
            {"answerable_by_code": "partial",
             "reason": "controls whose own text names no fleet repo are a mechanical candidate set "
                       "for portability; whether they actually transfer cleanly can only be shown by "
                       "another factory adopting them, which is outside this repo's data"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
