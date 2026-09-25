"""Q14.xx / RQ-h5-014 -- Of changes to the control register, what share
come from the factory owner directly versus an agent-run sync?
register_history.sha joined to git.commits' actor classification
(v_commits view: human/agent/bot).
"""
RQ_ID = "RQ-h5-014"
QUESTION = "Of changes to the control register, what share come from the owner directly versus an agent-run sync?"


def answer(con):
    shas = con.execute("SELECT DISTINCT sha FROM knowledge.register_history").fetchall()
    counts = {"human": 0, "agent": 0, "bot": 0, "unmatched": 0}
    for (sha,) in shas:
        row = con.execute("SELECT actor FROM v_commits WHERE sha = ? LIMIT 1", (sha,)).fetchone()
        counts[row["actor"] if row else "unmatched"] += 1
    return [counts]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
