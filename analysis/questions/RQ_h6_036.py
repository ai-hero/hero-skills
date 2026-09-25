"""Q10.xx / RQ-h6-036 -- Of the conventions the fleet map says every repo
follows, what share is enforced by an automated check versus prose only?
Proxy: knowledge.checks now has real control_id/title text (post-fix, see
README) -- counts controls with at least one linked check versus none.
"""
RQ_ID = "RQ-h6-036"
QUESTION = "Of the conventions the fleet map says every repo follows, what share is enforced by an automated check?"


def answer(con):
    controls = con.execute("SELECT control_id FROM knowledge.controls").fetchall()
    total = len(controls)
    with_check = con.execute(
        "SELECT COUNT(DISTINCT control_id) FROM knowledge.checks WHERE control_id IS NOT NULL AND control_id != ''"
    ).fetchone()[0]
    return [{"controls": total, "controls_with_at_least_one_check": with_check,
             "enforced_share": round(with_check / total, 3) if total else None}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
