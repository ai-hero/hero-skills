"""Q11.xx / RQ-h3-014 -- At what rate are commits reverted and merged PRs
reopened or sent back for rework?

commits.is_revert is set by ingest/git.py's REVERT_SHA_RE (git's own
"This reverts commit ..." body marker). "Reopened" = a pr_timeline row with
event='reopened' -- pr_timeline only carries the event kinds github.py
listed in TIMELINE_EVENTS, which does include reopened.
"""
RQ_ID = "RQ-h3-014"
QUESTION = "At what rate are commits reverted and merged PRs reopened?"

SQL = """
SELECT repo,
       (SELECT COUNT(*) FROM git.commits c WHERE c.repo = r.repo) AS commits,
       (SELECT COUNT(*) FROM git.commits c WHERE c.repo = r.repo AND c.is_revert = 1) AS reverts,
       (SELECT COUNT(*) FROM github.prs p WHERE p.repo = r.repo) AS prs,
       (SELECT COUNT(DISTINCT t.number) FROM github.pr_timeline t WHERE t.repo = r.repo AND t.event = 'reopened') AS reopened_prs
FROM git.repos r
ORDER BY reverts DESC
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["revert_rate"] = round(d["reverts"] / d["commits"], 4) if d["commits"] else None
        d["reopen_rate"] = round(d["reopened_prs"] / d["prs"], 4) if d["prs"] else None
        out.append(d)
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
