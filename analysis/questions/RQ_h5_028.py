"""Q14.xx / RQ-h5-028 -- How often is a cached snapshot of an external
source refreshed relative to how often the source itself changes?
design_releases/design_rounds tables aren't populated by any ingest script
here (no design-export ingest exists), so "cached snapshot" has no
concrete table to measure -- not answerable without that ingest.
"""
RQ_ID = "RQ-h5-028"
QUESTION = "How often is a cached snapshot of an external source refreshed relative to how often the source changes?"


def answer(con=None):
    return [{"answerable_by_code": False,
             "reason": "no design_releases/design_rounds (or similar cached-snapshot) table is ingested by any script here"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
