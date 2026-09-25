"""Q13.xx / RQ-h4-030 -- Have the guardrails a repo puts on itself (pinned
modes, do-not-ship markers, feature flags) ever been the thing that broke
a release?

A keyword co-occurrence proxy (a commit mentioning a guardrail word and a
break/broke word) is noise: ordinary feature and scanning commits match it
without any guardrail-caused break. The words are too common on their own
to co-occur meaningfully across a redacted commit body. Not publishing that
as an answer.
"""
RQ_ID = "RQ-h4-030"
QUESTION = "Have the guardrails a repo puts on itself ever been the thing that broke a release?"


def answer(con=None):
    return [{"answerable_by_code": False,
             "reason": "keyword co-occurrence (guardrail word + break word) is noise, not signal -- "
                       "spot-checked matches were false positives; would need reading each candidate's "
                       "actual diff/incident record, not done here"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
