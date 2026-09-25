"""Q8 / RQ-h4-027 -- Do the clones' implementations of a shared architectural pattern still match each other?

Not code-answerable: method='deferred', status='deferred', defer_reason='code-deep-dive'.
Needs reading product code in every clone, which is out of scope. The register's checks answer a narrower version.

This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "RQ-h4-027"
QUESTION = "Do the clones' implementations of a shared architectural pattern still match each other?"


def answer(con=None):
    return [{"answerable_by_code": False, "method": 'deferred', "status": 'deferred',
             "needs": "owner retrospective interview"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
