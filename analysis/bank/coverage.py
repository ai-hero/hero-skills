"""How much of the question bank has an implementation.

python3 bank/coverage.py             # summary by status/method
python3 bank/coverage.py --missing   # list unimplemented "now" questions, sql/detector first
"""
import csv, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "questions.csv")
QUESTIONS_DIR = os.path.join(os.path.dirname(HERE), "questions")

# coding-first ordering: pure sql and detector-backed questions need no LLM
# at runtime, so they're implemented before haiku/human ones.
METHOD_RANK = {"sql": 0, "detector": 1, "sql + detector": 1, "haiku": 2, "sql + haiku": 2,
               "detector + haiku": 2, "human": 3, "sql + human": 3, "detector + human": 3,
               "haiku + human": 3, "deferred": 4}


def implemented_ids():
    ids = set()
    for name in os.listdir(QUESTIONS_DIR):
        if not name.endswith(".py") or name in ("__init__.py", "runner.py"):
            continue
        text = open(os.path.join(QUESTIONS_DIR, name)).read()
        m = re.search(r'RQ_ID\s*=\s*"([^"]+)"', text)
        if m:
            ids.add(m.group(1))
    return ids


def main():
    rows = list(csv.DictReader(open(CSV_PATH)))
    done = implemented_ids()

    by_status = {}
    for r in rows:
        by_status.setdefault(r["status"] or "(blank)", [0, 0])
        by_status[r["status"] or "(blank)"][0] += 1
        if r["rq_id"] in done:
            by_status[r["status"] or "(blank)"][1] += 1

    print(f"{len(done)} implemented / {len(rows)} total questions\n")
    print(f"{'status':12} {'done':>5} / {'total':<5}")
    for status, (total, n_done) in sorted(by_status.items()):
        print(f"{status:12} {n_done:>5} / {total:<5}")

    if "--missing" in sys.argv:
        now_missing = [r for r in rows if r["status"] == "now" and r["rq_id"] not in done]
        now_missing.sort(key=lambda r: METHOD_RANK.get(r["method"], 9))
        print(f"\n{len(now_missing)} 'now' questions still unimplemented (coding-first order):")
        for r in now_missing:
            print(f"  {r['rq_id']:14} [{r['method']:16}] {r['question'][:90]}")


if __name__ == "__main__":
    main()
