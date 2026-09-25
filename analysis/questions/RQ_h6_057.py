"""Q10.xx / RQ-h6-057 -- How reliable is the automated detection of the
owner correcting or interrupting an agent? Reports the regex-flag precision
against the Haiku label: a flagged prompt the model calls 'correction' or
'redirect' is a true positive; 'approval'/'question'/'other' is a false
positive on the regex's own terms -- this measures the FLAG's precision,
not the model's own accuracy (there's no ground truth beyond the model).
"""
RQ_ID = "RQ-h6-057"
QUESTION = "How reliable is the automated detection of the owner correcting or interrupting an agent?"

STEERING_KINDS = ("correction", "redirect")


def answer(con):
    rows = con.execute(
        "SELECT pk.kind, COUNT(*) AS n FROM detectors.prompt_kind_by_prompt p "
        "JOIN detectors.prompt_kind pk ON pk.content_hash = p.content_hash "
        "WHERE p.flagged = 1 GROUP BY pk.kind"
    ).fetchall()
    total = sum(r["n"] for r in rows)
    steering = sum(r["n"] for r in rows if r["kind"] in STEERING_KINDS)
    return [{"regex_flagged_prompts": total, "haiku_confirms_steering": steering,
             "regex_flag_precision": round(steering / total, 3) if total else None,
             "note": "measures the regex flag's precision against the Haiku label, not against human ground truth"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
