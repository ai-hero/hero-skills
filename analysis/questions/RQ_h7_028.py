"""Q4.xx / RQ-h7-028 -- Which design-record disciplines hold by
convention alone and which need a mechanical check? Cross-references
NEW-C15-01's why-coverage with RQ-h6-036's check-coverage: a discipline
with a control but no linked check holds by convention alone. Staleness
(the question's second half) is code commits since DESIGN.md last changed.
"""
RQ_ID = "RQ-h7-028"
QUESTION = "Which design-record disciplines hold by convention alone, and which need a mechanical check?"


def answer(con):
    rows = con.execute(
        "SELECT c.control_id, c.title FROM knowledge.controls c "
        "WHERE c.control_id NOT IN (SELECT DISTINCT control_id FROM knowledge.checks WHERE control_id IS NOT NULL AND control_id != '')"
    ).fetchall()
    staleness = con.execute(
        "SELECT d.repo, d.last_touch, COUNT(DISTINCT c.sha) AS code_commits_since "
        "FROM (SELECT c.repo, MAX(c.day) AS last_touch FROM git.commit_files f "
        "      JOIN git.commits c ON c.repo = f.repo AND c.sha = f.sha "
        "      WHERE f.path = 'DESIGN.md' GROUP BY c.repo) d "
        "LEFT JOIN git.commits c ON c.repo = d.repo AND c.day > d.last_touch "
        "     AND EXISTS (SELECT 1 FROM git.commit_files f WHERE f.repo = c.repo AND f.sha = c.sha "
        "                 AND f.path NOT LIKE '%.md') "
        "GROUP BY d.repo ORDER BY code_commits_since DESC"
    ).fetchall()
    return ([{"controls_with_no_linked_check_convention_only": len(rows)}] + [dict(r) for r in rows[:20]]
            + [{"design_md_staleness": [dict(r) for r in staleness],
                "note": "DESIGN.md has no check; staleness = code commits after its last change"}])


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
