"""Q10.xx / RQ-h6-020 -- Do individual repos invent process conventions
that the process plugin doesn't document? Proxy: each repo's own
CLAUDE.md/AGENTS.md size, via doc_versions -- a repo whose file is much
larger than the fleet's smallest (the template's own, presumably closest
to "just what the plugin vendors") is carrying extra local convention text,
not proof of invented rules specifically, but a size signal worth reading
that way.
"""
RQ_ID = "RQ-h6-020"
QUESTION = "Do individual repos invent process conventions that the process plugin doesn't document?"


def answer(con):
    rows = con.execute(
        "SELECT repo, doc, bytes FROM knowledge.doc_versions d WHERE doc IN ('CLAUDE.md', 'AGENTS.md') "
        "AND ts = (SELECT MAX(ts) FROM knowledge.doc_versions d2 WHERE d2.repo = d.repo AND d2.doc = d.doc)"
    ).fetchall()
    if not rows:
        return [{"note": "no CLAUDE.md/AGENTS.md snapshots found"}]
    baseline = min(r["bytes"] for r in rows)
    return [dict(r, bytes_beyond_smallest=r["bytes"] - baseline) for r in
            sorted(rows, key=lambda r: -r["bytes"])]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
