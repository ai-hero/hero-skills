"""Q13.xx / RQ-h4-014 -- How often does the factory's own documentation
state something false, and is it corrected before or after it causes a
problem? Not computable from ingested data: verifying a documentation
claim against reality is a semantic judgment per claim, and no
doc-to-incident linkage is tracked. D2 drift covers staleness (design
record vs code timestamps), not falsity of specific statements.
"""
RQ_ID = "RQ-h4-014"
QUESTION = "How often does the factory's own documentation state something false, and is it corrected before or after it causes a problem?"


def answer(con):
    return [{"answerable_by_code": False,
             "reason": "D2 (detectors.drift) tracks staleness of design records against code "
                       "timestamps, not the truth of individual statements; verifying a specific "
                       "doc claim against reality, and linking its correction to whether a problem "
                       "preceded it, needs a human or a dedicated fact-check pass not built here"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
