"""Q17.xx / RQ-h2-032 -- How stale is a repo's design record relative to
its commit activity, and does that gap track spend? Combines RQ-h4-006's
DESIGN.md touch frequency with D9's per-repo spend.
"""
RQ_ID = "RQ-h2-032"
QUESTION = "How stale is a repo's design record relative to its commit activity, and does that gap track spend?"


def answer(con):
    from questions.RQ_h4_006 import answer as base_answer
    touches = {r["repo"]: r["design_md_commits"] for r in base_answer(con)}
    spend = {r["repo"]: r["cost_usd"] for r in con.execute(
        "SELECT repo, SUM(cost_usd) AS cost_usd FROM detectors.session_spend GROUP BY repo"
    ).fetchall()}
    all_commits = {r["repo"]: r["n"] for r in con.execute(
        "SELECT repo, COUNT(*) AS n FROM git.commits GROUP BY repo"
    ).fetchall()}
    out = []
    for repo, dmc in touches.items():
        total_commits = all_commits.get(repo, 0)
        out.append({"repo": repo, "design_md_touch_rate": round(dmc / total_commits, 4) if total_commits else None,
                    "spend": round(spend.get(repo, 0), 2)})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
