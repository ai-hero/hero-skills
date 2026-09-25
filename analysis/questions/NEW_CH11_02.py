"""Q11.xx / NEW-CH11-02 -- How does the review load per merged change
compare with what large public repos see? Reports this fleet's own
reviews-per-merged-PR number; the public-repo comparison baseline isn't
data this pipeline has (no external repos ingested) -- a human/literature
comparison, not a query.
"""
RQ_ID = "NEW-CH11-02"
QUESTION = "How does the review load per merged change compare with large public repos?"


def answer(con):
    row = con.execute(
        "SELECT COUNT(DISTINCT p.repo || ':' || p.number) AS merged_prs, COUNT(*) AS reviews "
        "FROM github.prs p JOIN github.pr_reviews r ON r.repo = p.repo AND r.number = p.number "
        "WHERE p.merged_ts IS NOT NULL"
    ).fetchone()
    return [{"merged_prs": row["merged_prs"], "reviews": row["reviews"],
             "reviews_per_merged_pr": round(row["reviews"] / row["merged_prs"], 2) if row["merged_prs"] else None,
             "note": "no external/public-repo baseline is ingested -- this fleet's own number only"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
