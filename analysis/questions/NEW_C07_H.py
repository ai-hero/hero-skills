"""Q11.xx / NEW-C07-H -- When a repo acts on a message from another
repo, how much does the work's scope change after the recipient looks
at its own code? sql half: change-set size (D1) for downstream
propagation commits, compared to the fleet-wide change-set size
distribution, as a rough scope-growth signal. Whether a given
downstream commit's scope actually grew *because of* something the
recipient found needs a human or Haiku read of the two change sets.
"""
RQ_ID = "NEW-C07-H"
QUESTION = "When a repo acts on a message from another repo, how much does the work's scope change after it looks at its own code?"


def answer(con):
    downstream_shas = con.execute(
        "SELECT DISTINCT downstream_repo AS repo, downstream_sha AS sha FROM detectors.propagation"
    ).fetchall()
    sizes = []
    for r in downstream_shas:
        row = con.execute(
            "SELECT insertions, deletions, files_changed FROM git.commits WHERE repo=? AND sha=?",
            (r["repo"], r["sha"]),
        ).fetchone()
        if row:
            sizes.append((row["insertions"] or 0) + (row["deletions"] or 0))
    fleet_avg = con.execute(
        "SELECT AVG(insertions + deletions) AS avg_size FROM git.commits"
    ).fetchone()["avg_size"]
    return [{"downstream_adoption_commits": len(sizes),
             "avg_downstream_adoption_change_size": round(sum(sizes) / len(sizes), 1) if sizes else None,
             "fleet_wide_avg_commit_change_size": round(fleet_avg, 1) if fleet_avg else None,
             "answerable_by_code": "partial",
             "reason": "average change size of downstream-adoption commits vs the fleet baseline is "
                       "above as a rough signal; attributing size growth specifically to something "
                       "found while acting on the message (vs. unrelated work in the same commit) "
                       "needs a human or Haiku read"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
