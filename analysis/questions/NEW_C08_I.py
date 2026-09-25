"""Q14.xx / NEW-C08-I -- Is there a check that catches a stale or
diverged exported snapshot before it's used? Proxy: checks whose title
mentions "stale"/"snapshot"/"export"/"sync".
"""
RQ_ID = "NEW-C08-I"
QUESTION = "Is there a check that catches a stale or diverged exported snapshot before it's used?"


def answer(con):
    rows = con.execute(
        "SELECT check_id, title FROM knowledge.checks WHERE title LIKE '%stale%' OR title LIKE '%snapshot%' "
        "OR title LIKE '%export%' OR title LIKE '%sync%'"
    ).fetchall()
    return [{"matching_checks": len(rows)}] + [dict(r) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
