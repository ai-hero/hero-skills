"""Q11.xx / RQ-h3-019 -- How do tool-call error rates and human correction
rates trend over the study? Tool-call error rate from tool_calls.is_error;
correction rate reuses the Haiku prompt_kind classifier's monthly trend
(RQ-h7-038 already computes it) joined side by side.
"""
RQ_ID = "RQ-h3-019"
QUESTION = "How do tool-call error rates and human correction rates trend over the study?"

ERROR_SQL = """
SELECT substr(ts, 1, 7) AS month, COUNT(*) AS tool_calls, SUM(is_error) AS errors
FROM harness.tool_calls WHERE ts IS NOT NULL GROUP BY month
"""


def answer(con):
    from questions.RQ_h7_038 import answer as interaction_answer
    correction_by_month = {r["month"]: r["steering_share"] for r in interaction_answer(con)}
    errors = {r["month"]: r for r in con.execute(ERROR_SQL).fetchall()}
    out = []
    for month in sorted(set(errors) | set(correction_by_month)):
        e = errors.get(month)
        out.append({
            "month": month,
            "tool_calls": e["tool_calls"] if e else None,
            "tool_error_rate": round(e["errors"] / e["tool_calls"], 4) if e else None,
            "steering_prompt_share": correction_by_month.get(month),
        })
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
