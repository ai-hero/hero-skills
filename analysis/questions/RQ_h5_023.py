"""Q14.xx / RQ-h5-023 -- How often is an agent-instruction file or design
record found stale or self-contradictory? Same D2 drift signal as
RQ-h3-012, plus RQ-h6-037's below-fleet-median section-count flag as a
second "looks thin/stale" signal.
"""
RQ_ID = "RQ-h5-023"
QUESTION = "How often is an agent-instruction file or design record found stale or self-contradictory?"


def answer(con):
    drift = con.execute("SELECT COUNT(*) FROM detectors.drift WHERE drifted_now = 1").fetchone()[0]
    from questions.RQ_h6_037 import answer as sections_answer
    rows = sections_answer(con)
    below_median = sum(1 for r in rows if isinstance(r, dict) and r.get("below_fleet_median"))
    return [{"repos_with_drifted_instruction_file": drift, "repos_below_fleet_median_design_record_size": below_median}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
