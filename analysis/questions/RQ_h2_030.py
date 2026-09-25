"""Q16.xx / RQ-h2-030 -- Do the factory's gates actually block a failing
change, or do they pass everything through eventually? D8-backed: gate_firings
review verdicts and CI catches, as a share of all PRs -- a gate that fires
"caught"/"CHANGES_REQUESTED" on some share of traffic is blocking something;
one that never does isn't (see RQ-cicd-006 for the per-workflow never-failed list).
"""
RQ_ID = "RQ-h2-030"
QUESTION = "Do the factory's gates actually block a failing change, or does everything pass through eventually?"


def answer(con):
    total_prs = con.execute("SELECT COUNT(*) FROM github.prs").fetchone()[0]
    changes_requested = con.execute(
        "SELECT COUNT(DISTINCT ref) FROM detectors.gate_firings WHERE gate_kind = 'review' AND verdict = 'CHANGES_REQUESTED'"
    ).fetchone()[0]
    ci_catches = con.execute("SELECT COUNT(*) FROM detectors.gate_firings WHERE gate_kind = 'ci'").fetchone()[0]
    return [{"total_prs": total_prs, "prs_with_changes_requested": changes_requested,
             "changes_requested_share": round(changes_requested / total_prs, 3) if total_prs else None,
             "ci_catches_fleet_wide": ci_catches}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
