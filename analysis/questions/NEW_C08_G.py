"""Q14.xx / NEW-C08-G -- Of detected violations, what share are fixed
immediately, deferred, or carved out and never revisited?
check_results '❌' rows joined against plan_items whose title mentions
the check_id -- weak text-match linkage (no explicit check<->item column),
so "fixed" here means "a plan item referencing this check exists and is
done," not a confirmed causal fix.
"""
RQ_ID = "NEW-C08-G"
QUESTION = "Of detected violations, what share are fixed immediately, deferred, or never revisited?"


def answer(con):
    fails = con.execute(
        "SELECT DISTINCT repo, check_id FROM knowledge.check_results WHERE result = '❌'"
    ).fetchall()
    total = len(fails)
    matched_done = matched_open = unmatched = 0
    for r in fails:
        item = con.execute(
            "SELECT status FROM plans.plan_items WHERE repo = ? AND title LIKE ? LIMIT 1",
            (r["repo"], f"%{r['check_id']}%"),
        ).fetchone()
        if not item:
            unmatched += 1
        elif item[0] in ("done", "delivered"):
            matched_done += 1
        else:
            matched_open += 1
    return [{"repo_check_failures": total, "matched_to_a_done_item": matched_done,
             "matched_to_an_open_item": matched_open, "no_matching_item_found": unmatched}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
