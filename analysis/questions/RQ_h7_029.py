"""Q4.xx / RQ-h7-029 -- How reliable are the factory's security-process
signals, such as a review with no findings while a parallel review finds
a critical issue? Proxy: PRs where one reviewer approved and another
requested changes on the same PR -- a disagreement signal in the review
process itself.
"""
RQ_ID = "RQ-h7-029"
QUESTION = "How reliable are the factory's security-process signals -- do reviewers ever disagree on the same PR?"


def answer(con):
    rows = con.execute(
        "SELECT repo, number, GROUP_CONCAT(DISTINCT state) AS states FROM github.pr_reviews "
        "GROUP BY repo, number HAVING states LIKE '%APPROVED%' AND states LIKE '%CHANGES_REQUESTED%'"
    ).fetchall()
    total_reviewed_prs = con.execute("SELECT COUNT(DISTINCT repo || ':' || number) FROM github.pr_reviews").fetchone()[0]
    return [{"reviewed_prs": total_reviewed_prs, "prs_with_both_approve_and_changes_requested": len(rows),
             "disagreement_share": round(len(rows) / total_reviewed_prs, 3) if total_reviewed_prs else None}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
