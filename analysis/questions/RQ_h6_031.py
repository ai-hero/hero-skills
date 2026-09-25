"""Q10.xx / RQ-h6-031 -- Does a new model, a harness feature or a
rewritten skill description change how often that skill is invoked?
Proxy: skill_versions change events (any modify, not just merges) matched
against the skill's tool_calls invocation count in the 30 days before vs
after.
"""
RQ_ID = "RQ-h6-031"
QUESTION = "Does a rewritten skill description change how often that skill is invoked?"


def answer(con):
    import datetime as dt
    changes = con.execute(
        "SELECT skill, day FROM knowledge.skill_versions WHERE change_type = 'modify' ORDER BY skill, day"
    ).fetchall()
    out = []
    for r in changes[:200]:
        d = dt.datetime.fromisoformat(r["day"])
        before = con.execute(
            "SELECT COUNT(*) FROM harness.tool_calls WHERE skill_name LIKE ? AND ts < ? AND ts > ?",
            (f"%{r['skill']}%", r["day"], (d - dt.timedelta(days=14)).date().isoformat()),
        ).fetchone()[0]
        after = con.execute(
            "SELECT COUNT(*) FROM harness.tool_calls WHERE skill_name LIKE ? AND ts > ? AND ts < ?",
            (f"%{r['skill']}%", r["day"], (d + dt.timedelta(days=14)).date().isoformat()),
        ).fetchone()[0]
        if before or after:
            out.append({"skill": r["skill"], "changed_on": r["day"], "invocations_14d_before": before,
                        "invocations_14d_after": after})
    return out[:25]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
