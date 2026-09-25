"""Q3.xx / NEW-C02-03 -- How long does verification wait on a human to
supply credentials (cloud or infrastructure logins), and how often does
that block a merge? Keyword proxy over PR bodies/titles, following the
same honest-proxy pattern as RQ-h6-028: a naive keyword hit is reported
as a candidate count, not a validated answer.
"""
RQ_ID = "NEW-C02-03"
QUESTION = "How long does verification wait on a human to supply credentials, and how often does that block a merge?"

_KEYWORDS = ["credential", "login", "api key", "waiting on", "needs access", "locked out",
             "2fa", "sso", "permission denied"]


def answer(con):
    rows = con.execute(
        "SELECT repo, number, title, body_redacted, hours_to_merge, hours_open, merged_ts "
        "FROM github.prs WHERE body_redacted IS NOT NULL"
    ).fetchall()
    hits = []
    for r in rows:
        text = (r["title"] or "") + " " + (r["body_redacted"] or "")
        text_l = text.lower()
        if any(kw in text_l for kw in _KEYWORDS):
            hits.append({"repo": r["repo"], "number": r["number"],
                        "hours_open": r["hours_open"], "merged": r["merged_ts"] is not None})
    return [{"candidate_credential_blocked_prs": len(hits), "total_prs_scanned": len(rows),
             "sample": hits[:10],
             "answerable_by_code": "partial",
             "reason": "this is a raw keyword match on PR title/body, not a verified count -- it "
                       "will both miss credential waits never mentioned in the PR text and catch "
                       "unrelated mentions (e.g. a PR that just adds a credentials file); a human "
                       "should spot-check the sample before trusting the count"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
