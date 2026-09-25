"""Run one or all answered question files against the cube.

Usage:
    python3 questions/runner.py                 # run every question module
    python3 questions/runner.py RQ-h1-042        # run one, by rq_id

Each questions/RQ_<id>.py module declares:
    RQ_ID    = "RQ-h1-042"          # matches bank/questions.csv rq_id
    QUESTION = "..."                # human-readable, for the printed header
    def answer(con): -> list[dict]  # con is the connected cube (cube.db.connect())

A question file never opens its own sqlite connection or re-reads a repo --
everything it needs is a query over the cube's attached sources and views.
"""
import csv, importlib, os, pkgutil, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cube.db import connect

HERE = os.path.dirname(os.path.abspath(__file__))
BANK = os.path.join(os.path.dirname(HERE), "bank", "questions.csv")


def bank_row(rq_id):
    with open(BANK) as f:
        for row in csv.DictReader(f):
            if row["rq_id"] == rq_id:
                return row
    return None


def discover():
    for _, name, _ in pkgutil.iter_modules([HERE]):
        if name in ("runner", "__init__"):
            continue
        yield importlib.import_module(f"questions.{name}")


def run_one(mod, con):
    row = bank_row(mod.RQ_ID)
    status = row["status"] if row else "?"
    print(f"\n=== {mod.RQ_ID} [{status}] {mod.QUESTION}")
    result = mod.answer(con)
    for r in result:
        print(" ", dict(r) if hasattr(r, "keys") else r)
    return result


def main():
    con = connect()
    target = sys.argv[1] if len(sys.argv) > 1 else None
    mods = list(discover())
    if target:
        mods = [m for m in mods if m.RQ_ID == target]
        if not mods:
            sys.exit(f"no question module for {target}")
    for mod in mods:
        run_one(mod, con)


if __name__ == "__main__":
    main()
