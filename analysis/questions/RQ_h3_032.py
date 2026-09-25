"""Q11.xx / RQ-h3-032 -- Does a repo's documentation ever claim a security
control is in place when check_results says it doesn't hold? Proxy: for
each failing (❌) check, whether the repo's DESIGN.md mentions the
check's control_id anywhere (a doc claiming compliance with a control that
check_results says is failing).
"""
RQ_ID = "RQ-h3-032"
QUESTION = "Does a repo's documentation ever claim a security control is in place when it isn't?"


def answer(con):
    fails = con.execute(
        "SELECT DISTINCT cr.repo, c.control_id FROM knowledge.check_results cr "
        "JOIN knowledge.checks c ON c.check_id = cr.check_id "
        "WHERE cr.result = '❌' AND c.control_id IS NOT NULL AND c.control_id != ''"
    ).fetchall()
    contradictions = 0
    checked = 0
    for r in fails:
        doc = con.execute(
            "SELECT text_redacted FROM knowledge.design_decisions WHERE repo = ? LIMIT 50", (r["repo"],)
        ).fetchall()
        text = " ".join(d[0] or "" for d in doc)
        if not text:
            continue
        checked += 1
        if r["control_id"] in text:
            contradictions += 1
    return [{"failing_checks_with_a_control_id": len(fails), "repos_with_design_decisions_checked": checked,
             "control_id_mentioned_despite_failing": contradictions}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
