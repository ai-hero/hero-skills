"""Q14.xx / RQ-h5-007 -- At each compliance sync, what fraction of repos
pass each control the template defines?
"""
RQ_ID = "RQ-h5-007"
QUESTION = "At each compliance sync, what fraction of repos pass each control?"

SQL = """
SELECT c.control_id, cr.result, COUNT(*) AS n
FROM knowledge.check_results cr
JOIN knowledge.checks c ON c.check_id = cr.check_id
WHERE c.control_id IS NOT NULL AND c.control_id != ''
GROUP BY c.control_id, cr.result
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    by_control = {}
    for r in rows:
        by_control.setdefault(r["control_id"], {}).setdefault(r["result"], r["n"])
    out = []
    for cid, counts in sorted(by_control.items()):
        passed = counts.get("✅", 0)
        failed = counts.get("❌", 0)
        if passed + failed:
            out.append({"control_id": cid, "pass": passed, "fail": failed,
                        "pass_rate": round(passed / (passed + failed), 3)})
    return sorted(out, key=lambda x: x["pass_rate"])[:20]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
