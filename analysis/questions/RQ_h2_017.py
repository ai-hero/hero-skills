"""Q16.xx / RQ-h2-017 -- How much model spend do scripted gates save
compared to asking the model to decide the same thing? No before/after
measurement of a specific scripted-gate migration is captured anywhere --
not answerable without that pairing existing in the data.
"""
RQ_ID = "RQ-h2-017"
QUESTION = "How much model spend do scripted gates save compared to asking the model to decide?"


def answer(con=None):
    return [{"answerable_by_code": False,
             "reason": "no before/after spend measurement of a specific scripted-gate migration is "
                       "recorded anywhere (see Q2.05's own grounding: 'most were not measured')"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
