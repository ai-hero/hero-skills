"""Q11.xx / RQ-h3-010 -- How often does an automated check report success
while not performing the check it claims to? No "did the check actually
execute its logic" signal exists (check_results only has the verdict, not
an execution trace) -- not answerable without reading each checker's
implementation, which the register audit already does manually (see the
plugin's own compliance-engine incident history in controls.raw_json's
`why:` fields, e.g. C-GATES's own dead-config incident).
"""
RQ_ID = "RQ-h3-010"
QUESTION = "How often does an automated check report success while not performing the check it claims to?"


def answer(con=None):
    return [{"answerable_by_code": False,
             "reason": "check_results has only pass/fail, no execution trace to verify the check "
                       "actually ran its logic -- would need reading each checker's implementation"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
