"""Q2.xx / NEW-PF-06 -- Does every check the factory relies on (CI, review
agents, the judge, compliance) actually run and report a result? D8+D10-
backed: checks defined in the register (knowledge.checks) against whether
each ever appears in check_results at all.
"""
RQ_ID = "NEW-PF-06"
QUESTION = "Does every check the factory relies on actually run and report a result?"


def answer(con):
    defined = {r[0] for r in con.execute("SELECT DISTINCT check_id FROM knowledge.checks").fetchall()}
    ran = {r[0] for r in con.execute("SELECT DISTINCT check_id FROM knowledge.check_results").fetchall()}
    never_ran = sorted(defined - ran)
    return [{"checks_defined": len(defined), "checks_with_at_least_one_result": len(ran & defined),
             "defined_but_never_ran": never_ran}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
