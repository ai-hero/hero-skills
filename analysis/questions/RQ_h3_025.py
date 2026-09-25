"""Q11.xx / RQ-h3-025 -- Are supply-chain safeguards (digest pins, action
SHA pins, dependency-update bots) in place fleet-wide? check_results for
the digest/pin-shaped checks (C-SUPPLY's checks) -- same pattern as
NEW-C06-01.
"""
RQ_ID = "RQ-h3-025"
QUESTION = "Are supply-chain safeguards (digest pins, action SHA pins, dependency updates) in place fleet-wide?"

SQL = """
SELECT DISTINCT cr.repo, c.check_id, c.title, cr.result
FROM knowledge.check_results cr
JOIN knowledge.checks c ON c.check_id = cr.check_id
WHERE c.control_id = 'C-SUPPLY'
ORDER BY c.check_id, cr.repo
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    by_check = {}
    for r in rows:
        b = by_check.setdefault(r["check_id"], {"title": r["title"], "pass": 0, "fail": 0})
        b["pass" if r["result"] == "✅" else "fail"] += r["result"] in ("✅", "❌")
    return [{"check_id": k, **v} for k, v in by_check.items()]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
