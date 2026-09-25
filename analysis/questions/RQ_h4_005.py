"""Q13.xx / RQ-h4-005 -- Do the template's shared agent instructions,
hooks and skills stay current with the process plugin, or drift? Same D2
drift signal as the main table (.claude/rules/comments.md), scoped to the
template repo alone.
"""
RQ_ID = "RQ-h4-005"
QUESTION = "Do the template's shared agent instructions, hooks and skills stay current with the process plugin?"


def answer(con):
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ingest.fleet import TEMPLATE_REPO
    if not TEMPLATE_REPO:
        return [{"note": "no FLEET.md group: template repo in this fleet"}]
    row = con.execute(
        "SELECT drifted_now, repo_last_touched_ts, source_last_touched_ts FROM detectors.drift WHERE repo = ?",
        (TEMPLATE_REPO,),
    ).fetchone()
    if not row:
        return [{"note": "no drift row for the template repo"}]
    return [dict(row)]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
