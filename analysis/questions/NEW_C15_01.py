"""Q19.xx / NEW-C15-01 -- Is there a record of why each factory rule,
gate or skill was added? Proxy: controls.raw_json's `why:` field;
reports its coverage.
"""
RQ_ID = "NEW-C15-01"
QUESTION = "Is there a record of why each factory rule, gate or skill was added?"


def answer(con):
    controls = con.execute("SELECT raw_json FROM knowledge.controls").fetchall()
    with_why = sum(1 for (raw,) in controls if "why:" in raw)
    checks = con.execute("SELECT raw_json FROM knowledge.checks").fetchall()
    checks_with_why = sum(1 for (raw,) in checks if "why:" in raw)
    return [{"controls": len(controls), "controls_with_why": with_why,
             "checks": len(checks), "checks_with_why": checks_with_why}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
