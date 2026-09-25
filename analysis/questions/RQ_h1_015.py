"""Q12.xx / RQ-h1-015 -- How many repos does the fleet hold each month, by
role, and at what template maturity was each one cloned?

"Held" = the calendar month falls between a repo's first and last ingested
commit month, inclusive -- a repo with a gap longer than a month between
commits still counts as held throughout (this only detects repos that never
came back at all, not ones that went quiet for a while).

"Template maturity at clone time" = age of hero-template, in days, on the
clone's first-commit date. Only meaningful for role='clone'.
"""
import datetime as dt

RQ_ID = "RQ-h1-015"
QUESTION = "How many repos does the fleet hold each month, by role, and at what template maturity was each one cloned?"

REPOS_SQL = "SELECT repo, role, first_commit_ts, last_commit_ts FROM git.repos"


def _month_range(start_month, end_month):
    y, m = int(start_month[:4]), int(start_month[5:7])
    ey, em = int(end_month[:4]), int(end_month[5:7])
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            m = 1; y += 1
    return out


def answer(con):
    rows = con.execute(REPOS_SQL).fetchall()
    template_first = min(r["first_commit_ts"] for r in rows if r["role"] == "template repo")
    template_dt = dt.datetime.fromisoformat(template_first)

    by_month_role = {}
    clone_maturity = []
    for r in rows:
        for month in _month_range(r["first_commit_ts"][:7], r["last_commit_ts"][:7]):
            by_month_role.setdefault((month, r["role"]), 0)
            by_month_role[(month, r["role"])] += 1
        if r["role"] == "clone":
            clone_dt = dt.datetime.fromisoformat(r["first_commit_ts"])
            clone_maturity.append({
                "repo": r["repo"],
                "cloned_on": r["first_commit_ts"][:10],
                "template_age_days_at_clone": (clone_dt - template_dt).days,
            })

    counts = [{"month": m, "role": role, "repos": n} for (m, role), n in sorted(by_month_role.items())]
    return counts + [{"clone_maturity_at_founding": clone_maturity}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
