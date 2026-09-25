"""Prompt-kind classifier -> detectors.sqlite, table prompt_kind.

Feeds the correction/steering question cluster (RQ-h7-005, RQ-h6-048,
RQ-h6-057, RQ-h7-007, RQ-h7-038, RQ-h7-045 and others) as a three-pass read:
  1. Keyword/regex pass (free) -- flags a candidate correction/decision.
  2. Haiku pass (cached) -- classifies the flagged ones only.
  3. Sonnet adjudication for low-confidence cases -- NOT implemented here;
     every row below is the Haiku label as-is, unreviewed.

Only regex-flagged prompts get a model call: most non-slash prompts are plain
task requests, not corrections, and sending all of them to Haiku would be the
same fixed-cost-per-batch problem D1 solves by batching, times a much larger n.
Batched like D1: ~40 prompts per `claude -p` call from a neutral cwd, cached by
content hash. A prompt whose batch failed, or whose id the reply left out, gets
no row, so the next run retries it instead of reading it as "other".
"""
import hashlib, json, os, re, sqlite3, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import OUT

DB_PATH = os.path.join(OUT, "detectors.sqlite")
HARNESS_DB = os.path.join(OUT, "harness.sqlite")
BATCH_SIZE = 40
MODEL = "haiku"
NEUTRAL_CWD = "/tmp"

# Deliberately broad: a miss here is never labelled, a false flag only costs a slot in a Haiku batch.
FLAG_RE = re.compile(
    r"you'?re right|no,\s|^no\b|stop\b|revert|i was wrong|actually\b|instead\b|"
    r"don'?t\b|wrong\b|that'?s not|please (undo|redo|fix)|rate limit",
    re.I,
)

PROMPT_HEADER = """You are classifying developer prompts sent to a coding agent, mid-session.
For each prompt below (id given), classify its KIND:
  "correction"  - the developer is fixing a mistake the agent made
  "approval"    - the developer is agreeing with / accepting the agent's proposal
  "redirect"    - the developer is changing direction, not because of a mistake
  "question"    - the developer is just asking something, no correction implied
  "other"       - none of the above fits

Reply with ONLY a JSON array, no prose, no markdown fence:
[{"id": <id>, "kind": "<one of the five>"}, ...]

Prompts:
"""


def content_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def call_haiku(batch, tries=3):
    lines = [PROMPT_HEADER]
    for local_id, text in batch:
        lines.append(f"--- id={local_id} ---\n{text[:400]}\n")
    prompt = "\n".join(lines)

    billed = 0.0  # every completed call is billed, including one whose reply won't parse
    for attempt in range(tries):
        try:
            # The labelled text is untrusted (anyone's prompt, pasted reviews), so the model gets no tools and no MCP.
            p = subprocess.run(
                ["claude", "-p", "--model", MODEL, "--effort", "low", "--output-format", "json",
                 "--tools", "", "--strict-mcp-config", "--permission-mode", "dontAsk"],
                input=prompt, capture_output=True, text=True, cwd=NEUTRAL_CWD, timeout=180 + attempt * 120,
            )
        except subprocess.TimeoutExpired:
            print(f"  ! claude -p timed out (try {attempt + 1}/{tries})", file=sys.stderr)
            continue
        if p.returncode != 0:
            print(f"  ! claude -p failed (try {attempt + 1}/{tries}): {p.stderr[:300]}", file=sys.stderr)
            continue
        try:
            outer = json.loads(p.stdout)
        except json.JSONDecodeError:
            print(f"  ! unparsable reply (try {attempt + 1}/{tries}): {p.stdout[:300]}", file=sys.stderr)
            continue
        billed += outer.get("total_cost_usd", 0.0) or 0.0
        text = (outer.get("result") or "").strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            print(f"  ! model didn't return clean JSON (try {attempt + 1}/{tries}): {text[:300]}", file=sys.stderr)
            continue
        out = {}
        for row in parsed if isinstance(parsed, list) else []:
            try:
                out[int(row["id"])] = row["kind"]
            except (KeyError, ValueError, TypeError):
                continue
        return out, billed
    return {}, billed


def build(limit=None, dry_run=False):
    if not os.path.exists(HARNESS_DB):
        sys.exit("detectors/d_prompt_kind.py needs .analysis/data/harness.sqlite -- run ingest/harness.py first")

    hcon = sqlite3.connect(HARNESS_DB)
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS prompt_kind (
            content_hash TEXT PRIMARY KEY, kind TEXT, method TEXT
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS prompt_kind_by_prompt (
            ts TEXT, repo TEXT, content_hash TEXT, flagged INTEGER
        )
    """)

    rows = hcon.execute("SELECT ts, repo, text_redacted FROM prompts WHERE is_slash_command = 0").fetchall()
    if limit:
        rows = rows[:limit]

    cached = {h for (h,) in con.execute("SELECT content_hash FROM prompt_kind").fetchall()}
    link_rows, to_label = [], {}
    for ts, repo, text in rows:
        if not text:
            continue
        h = content_hash(text)
        flagged = 1 if FLAG_RE.search(text) else 0
        link_rows.append((ts, repo, h, flagged))
        if flagged and h not in cached:
            to_label.setdefault(h, text)

    con.execute("DELETE FROM prompt_kind_by_prompt")
    con.executemany("INSERT INTO prompt_kind_by_prompt VALUES (?,?,?,?)", link_rows)
    con.commit()

    n_flagged = sum(1 for r in link_rows if r[3])
    print(f"{len(rows)} prompts: {n_flagged} regex-flagged, {len(cached)} already cached, "
          f"{len(to_label)} need Haiku", file=sys.stderr)

    if dry_run or not to_label:
        con.close(); hcon.close()
        return

    unique = list(to_label.items())
    total_cost, n_labelled = 0.0, 0
    for i in range(0, len(unique), BATCH_SIZE):
        chunk = unique[i:i + BATCH_SIZE]
        batch_input = [(j, text) for j, (h, text) in enumerate(chunk)]
        result, cost = call_haiku(batch_input)
        total_cost += cost
        for j, (h, text) in enumerate(chunk):
            if j in result:
                con.execute("INSERT OR REPLACE INTO prompt_kind VALUES (?,?,?)", (h, result[j], "haiku"))
                n_labelled += 1
        con.commit()
        print(f"  batch {i // BATCH_SIZE + 1}/{(len(unique) - 1) // BATCH_SIZE + 1}: "
              f"{len(chunk)} prompts, ${cost:.4f} (running total ${total_cost:.2f})", file=sys.stderr)

    con.close(); hcon.close()
    print(f"detectors.sqlite: prompt_kind updated, {n_labelled} new labels, ${total_cost:.2f} spent")
    if n_labelled < len(unique):
        print(f"  ! {len(unique) - n_labelled} flagged prompts left unlabelled (failed batch or missing id); "
              f"rerun to retry them", file=sys.stderr)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    lim = None
    for a in sys.argv[1:]:
        if a.startswith("--limit="):
            lim = int(a.split("=", 1)[1])
    build(limit=lim, dry_run=dry)
