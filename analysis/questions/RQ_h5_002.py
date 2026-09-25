"""Q14.xx / RQ-h5-002 -- How far does a repo's local copy of the control
register drift from the canonical one? register_history rows per repo
(fleet vs any repo with its own overlay, per _register_sources) as the
"local copy" signal (see ingest/knowledge.py's _register_sources). A fleet
with no local copies has nothing to drift.
"""
RQ_ID = "RQ-h5-002"
QUESTION = "How far does a repo's local copy of the control register drift from the canonical one?"


def answer(con):
    rows = con.execute(
        "SELECT file, COUNT(*) AS versions FROM knowledge.register_history GROUP BY file"
    ).fetchall()
    labels = {r["file"].split(":")[0] for r in rows}
    return [{"register_sources_with_history": sorted(labels),
             "note": "'fleet' is the canonical overlay; any other label is a repo carrying its own "
                     "local CONTROLS.yaml/CHECKS.yaml copy -- none here means no local copies exist"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
