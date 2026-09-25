"""Q15.xx / RQ-cicd-002 -- When a PR's CI goes red, who turns it green
(same session, a later session, a human)? No session-to-CI-run link exists
(ci_runs has no session_id_hash), so "which session" isn't answerable --
this reports the same-day vs later-day split as the closest available proxy
for "same sitting vs came back to it."
"""
RQ_ID = "RQ-cicd-002"
QUESTION = "When a PR's CI goes red, how long until it goes green -- same day or later?"

SQL = """
SELECT repo, workflow_name, head_sha, conclusion, created_ts
FROM github.ci_runs
WHERE conclusion IN ('failure', 'success')
ORDER BY repo, workflow_name, head_sha, created_ts
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    groups = {}
    for r in rows:
        groups.setdefault((r["repo"], r["workflow_name"], r["head_sha"]), []).append((r["conclusion"], r["created_ts"]))

    same_day = later_day = 0
    for seq in groups.values():
        for i, (concl, ts) in enumerate(seq):
            if concl != "failure":
                continue
            for concl2, ts2 in seq[i + 1:]:
                if concl2 == "success":
                    if ts2[:10] == ts[:10]:
                        same_day += 1
                    else:
                        later_day += 1
                    break
    return [{"failures_that_later_passed": same_day + later_day, "turned_green_same_day": same_day,
             "turned_green_a_later_day": later_day}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
