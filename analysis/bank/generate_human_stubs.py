"""Generate a question file for every bank row that genuinely can't be
code-answered: method == 'human' (needs the owner's own account of why/what
they were thinking) or status == 'deferred' (the bank itself says not now,
with a reason). These aren't placeholders for later engineering -- no query
would ever answer them, so a stub that says so plainly is the honest
"implementation," not a cop-out. Skips any rq_id that already has a file
(hand-written files, including ones that mix sql+human, are left alone).

Usage: python3 bank/generate_human_stubs.py
"""
import csv, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
QUESTIONS_DIR = os.path.join(os.path.dirname(HERE), "questions")
CSV_PATH = os.path.join(HERE, "questions.csv")


def module_name(rq_id):
    return "STUB_" + re.sub(r"[^A-Za-z0-9]", "_", rq_id).strip("_")


def existing_ids():
    done = set()
    for name in os.listdir(QUESTIONS_DIR):
        if not name.endswith(".py") or name in ("__init__.py", "runner.py"):
            continue
        text = open(os.path.join(QUESTIONS_DIR, name)).read()
        m = re.search(r'RQ_ID\s*=\s*"([^"]+)"', text)
        if m:
            done.add(m.group(1))
    return done


TEMPLATE = '''"""{chapter_label} / {rq_id} -- {question}

Not code-answerable: method={method!r}, status={status!r}{defer_reason}.
{background}
This file exists so bank/coverage.py counts it as accounted-for rather than
silently missing -- the retrospective interview with the owner
is where this gets an answer, not a re-run of this pipeline.
"""
RQ_ID = "{rq_id}"
QUESTION = {question!r}


def answer(con=None):
    return [{{"answerable_by_code": False, "method": {method!r}, "status": {status!r},
             "needs": "owner retrospective interview"}}]


if __name__ == "__main__":
    for row in answer():
        print(row)
'''


def build():
    done = existing_ids()
    rows = list(csv.DictReader(open(CSV_PATH)))
    written = 0
    for r in rows:
        if r["rq_id"] in done:
            continue
        if not (r["method"] == "human" or r["status"] == "deferred"):
            continue
        defer_reason = f", defer_reason={r['defer_reason']!r}" if r.get("defer_reason") else ""
        background = (r.get("background") or "").strip()
        background = f"{background}\n" if background else ""
        path = os.path.join(QUESTIONS_DIR, module_name(r["rq_id"]) + ".py")
        with open(path, "w") as f:
            f.write(TEMPLATE.format(
                chapter_label=f"Q{r.get('chapter', '?')}", rq_id=r["rq_id"],
                question=r["question"], method=r["method"], status=r["status"],
                defer_reason=defer_reason, background=background,
            ))
        written += 1
    print(f"wrote {written} stub question files")


if __name__ == "__main__":
    build()
