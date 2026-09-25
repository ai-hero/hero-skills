"""One row per change set and one per original commit, for the chapter 2 charts.

Every row carries its repo's category (app, app with no features yet, allied)
and the stage the repo had reached on that day (skills, work items, goals,
messages), so any chart can be cut by either without re-deriving them.
Out-of-scope repos are dropped here, once.
"""
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date
from functools import lru_cache

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import OUT_OF_SCOPE, category_of  # noqa: E402
from ingest.git import CONV_RE  # noqa: E402

STAGES = ["No skills yet", "Skills", "+ work items", "+ goals", "+ messages"]
CATEGORIES = ["app", "app, no features yet", "allied"]


def week_of(day):
    y, w, _ = date.fromisoformat(day[:10]).isocalendar()
    return f"{y}-W{w:02d}"


def rows(con, sql, args=()):
    return [dict(r) for r in con.execute(sql, args).fetchall()]


@lru_cache(maxsize=None)
def adoption(con):
    first_file = lambda path: {r["repo"]: r["d"] for r in rows(con, """
        SELECT c.repo, MIN(c.day) d FROM git.commit_files f JOIN git.commits c ON c.repo=f.repo AND c.sha=f.sha
        WHERE f.path = ? GROUP BY c.repo""", (path,))}
    hero = first_file("HERO.md")
    first_item = lambda goal: {r["repo"]: r["d"] for r in rows(con, f"""
        SELECT repo, MIN(day) d FROM plans.plan_items WHERE type {'=' if goal else '!='} 'goal' AND day IS NOT NULL
        GROUP BY repo""")}
    items, goals = first_item(False), first_item(True)
    msgs = {}
    for r in rows(con, "SELECT from_repo, to_repo, SUBSTR(created_ts,1,10) d FROM plans.messages"):
        for repo in (r["from_repo"], r["to_repo"]):
            if repo and r["d"] and r["d"] < msgs.get(repo, "9999"):
                msgs[repo] = r["d"]
    out = {}
    for r in rows(con, "SELECT repo, MIN(day) first, MAX(day) last, COUNT(*) n FROM git.commits GROUP BY repo"):
        if r["repo"] in OUT_OF_SCOPE:
            continue
        out[r["repo"]] = {**r, "skills": hero.get(r["repo"]), "items": items.get(r["repo"]),
                          "goals": goals.get(r["repo"]), "messages": msgs.get(r["repo"]),
                          "category": category_of(r["repo"])}
    return out


def stage_of(con, repo, day):
    a = adoption(con)[repo]
    on = lambda k: a[k] is not None and a[k] <= day
    return (STAGES[4] if on("messages") else STAGES[3] if on("goals") else STAGES[2] if on("items")
            else STAGES[1] if on("skills") else STAGES[0])


@lru_cache(maxsize=None)
def commit_facts(con):
    """Original commits: a merged PR's own commits where recovered, else the commit on main."""
    ad = adoption(con)
    units = {(r["repo"], r["main_sha"]): r for r in rows(con, "SELECT * FROM detectors.cs_units")}
    out = []
    main = rows(con, "SELECT repo, sha, day, subject, body_redacted, claude_trailer, is_bot, pr_number, "
                     "insertions + deletions churn FROM git.commits WHERE is_merge = 0")
    pr_commits = defaultdict(list)
    for r in rows(con, "SELECT repo, pr_number, sha, ts, subject, body_redacted, claude_trailer, author, "
                       "insertions + deletions churn FROM pr_commits.pr_commits WHERE is_merge = 0"):
        pr_commits[(r["repo"], r["pr_number"])].append(r)
    for m in main:
        if m["repo"] not in ad:
            continue
        u = units.get((m["repo"], m["sha"]))
        src = pr_commits.get((m["repo"], m["pr_number"])) if u and u["unit_kind"] == "pr" else None
        for c in src or [m]:
            day = (c.get("ts") or c.get("day"))[:10]
            bot = bool(m["is_bot"]) or "dependabot" in (c.get("author") or "").lower()
            out.append({
                "repo": m["repo"], "sha": c["sha"], "day": day, "week": week_of(day), "month": day[:7],
                "pr": m["pr_number"], "merged_day": m["day"], "subject": c["subject"],
                "body": c["body_redacted"] or "", "churn": c["churn"] or 0,
                "actor": "bot" if bot else "agent" if c["claude_trailer"] else "human",
                "conventional": bool(CONV_RE.match(c["subject"])),
                "category": ad[m["repo"]]["category"], "stage": stage_of(con, m["repo"], day),
                "original": src is not None,
            })
    return out


@lru_cache(maxsize=None)
def changeset_facts(con):
    """Change sets, dated by the day their PR (or pushed commit) landed on main."""
    ad = adoption(con)
    churn = {(c["repo"], c["sha"]): c["churn"] for c in commit_facts(con)}
    units = {(r["repo"], r["unit_kind"], r["unit_id"]): r for r in rows(con, "SELECT * FROM detectors.cs_units")}
    main_day = {(r["repo"], r["sha"]): r["day"] for r in rows(con, "SELECT repo, sha, day FROM git.commits")}
    sets = rows(con, "SELECT * FROM detectors.cs_sets")
    member = defaultdict(int)
    for s in sets:
        for sha in json.loads(s["shas_json"]):
            member[(s["repo"], sha)] += 1
    out = []
    for s in sets:
        if s["repo"] not in ad:
            continue
        u = units[(s["repo"], s["unit_kind"], s["unit_id"])]
        day = main_day.get((s["repo"], u["main_sha"]))
        if not day:
            continue
        shas = json.loads(s["shas_json"])
        out.append({
            "repo": s["repo"], "unit_kind": s["unit_kind"], "unit_id": s["unit_id"], "set_idx": s["set_idx"],
            "label": s["label"], "shas": shas, "n_commits": len(shas), "method": u["method"],
            "pr": int(s["unit_id"]) if s["unit_kind"] in ("pr", "pr-squash") else None,
            "day": day, "week": week_of(day), "month": day[:7],
            "lines": round(sum(churn.get((s["repo"], sha), 0) / member[(s["repo"], sha)] for sha in shas)),
            "category": ad[s["repo"]]["category"], "stage": stage_of(con, s["repo"], day),
            "dependabot": u["method"] == "dependabot",
        })
    return out


def weekly(facts, key, value=lambda f: 1, weeks=None, cats=None):
    """{category: [sum per week]} for facts grouped by key(f)."""
    acc = defaultdict(lambda: defaultdict(float))
    for f in facts:
        acc[key(f)][f["week"]] += value(f)
    cats = cats or sorted(acc)
    return {c: [round(acc[c].get(w, 0), 3) for w in weeks] for c in cats}
