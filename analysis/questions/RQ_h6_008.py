"""Q10.xx / RQ-h6-008 -- Does the clone-setup procedure write every
configuration field that other skills later read? Proxy: D10 presence at
a clone's first_commit snapshot for every artifact this pipeline checks,
same underlying data as RQ-h1-012, framed as a completeness check.
"""
RQ_ID = "RQ-h6-008"
QUESTION = "Does the clone-setup procedure write every configuration field that other skills later read?"


def answer(con):
    from questions.RQ_h1_012 import answer as base_answer
    rows = base_answer(con)
    out = []
    for r in rows:
        if not isinstance(r, dict) or "repo" not in r:
            continue
        artifacts = {k: v for k, v in r.items() if k != "repo"}
        missing = [k for k, v in artifacts.items() if not v]
        out.append({"repo": r["repo"], "missing_at_founding": missing})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
