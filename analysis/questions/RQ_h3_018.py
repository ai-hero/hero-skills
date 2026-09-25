"""Q11.xx / RQ-h3-018 -- When the compliance register reports different
pass rates for different repos, how much of that is a real gap versus a
check that doesn't apply (applies_to scoping) versus a check that's simply
broken for that repo? check_results.result carries '?' (n/a) and '–'
(not applicable/no data) alongside pass/fail -- these two are a documented
part of the answer, not noise to filter out.
"""
RQ_ID = "RQ-h3-018"
QUESTION = "How much of a compliance pass-rate gap between repos is real versus not-applicable versus broken?"

SQL = "SELECT repo, result, COUNT(*) AS n FROM knowledge.check_results GROUP BY repo, result"


def answer(con):
    rows = con.execute(SQL).fetchall()
    by_repo = {}
    for r in rows:
        by_repo.setdefault(r["repo"], {}).setdefault(r["result"], r["n"])
    out = []
    for repo, counts in sorted(by_repo.items()):
        total = sum(counts.values())
        passed = counts.get("✅", 0)
        failed = counts.get("❌", 0)
        na = counts.get("?", 0) + counts.get("–", 0)
        out.append({"repo": repo, "checks": total, "pass": passed, "fail": failed, "not_applicable_or_no_data": na,
                    "pass_rate_of_applicable": round(passed / (passed + failed), 3) if (passed + failed) else None})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
