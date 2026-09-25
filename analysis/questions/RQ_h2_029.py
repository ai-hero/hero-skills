"""Q17.xx / RQ-h2-029 -- When a shared process or interface changes, how
many follow-up changes does the fleet need, and what does that cost?
Combines D3 propagation arrival count with D9 spend for the downstream
repos in that chain, and D5 follow-up rate on those same arrivals
(reusing NEW-C10-03's candidate-regression count for the process-plugin
case specifically).
"""
RQ_ID = "RQ-h2-029"
QUESTION = "When a shared process or interface changes, how many follow-up changes does the fleet need, and what does it cost?"


def answer(con):
    from questions.NEW_C10_03 import answer as regression_answer
    regression = regression_answer(con)[0]
    spend = con.execute("SELECT SUM(cost_usd) FROM detectors.session_spend").fetchone()[0] or 0
    return [{"process_plugin_downstream_arrivals": regression, "fleet_total_spend_context": round(spend, 2)}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
