"""Q13.xx / RQ-h4-021 -- Does a repo converge on one policy for a
recurring design question (e.g. fail versus fall back on baseline)?
Not computable from ingested data: identifying a "recurring design
question" and checking whether repeated decisions converge to one
answer needs a human or Haiku read of each repo's design-decision log
over time, which is not ingested at that granularity.
"""
RQ_ID = "RQ-h4-021"
QUESTION = "Does a repo converge on one policy for a recurring design question (e.g. fail vs. fall back)?"


def answer(con):
    return [{"answerable_by_code": False,
             "reason": "no per-decision design-log ingest exists (only file-level touch timestamps "
                       "via D2/drift); identifying a recurring question and scoring convergence needs "
                       "a human or Haiku read of the actual decision entries over time"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
