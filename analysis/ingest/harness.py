"""Claude Code session transcripts, prompts, memories and the model/CC release
timeline -> data/harness.sqlite, on the shared ingest contract (ingest/fleet.py,
ingest/redact.py).
"""
import json, os, re, glob, sqlite3, hashlib, collections, datetime as dt, time, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import ALL_REPOS, ROOT, PLUGIN_REPO_NAME, REPO_ALIASES, dims
from ingest.redact import redact

HOME = os.path.expanduser("~")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".analysis", "data")
DB_PATH = os.path.join(OUT, "harness.sqlite")
TIMELINE_CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bank", "timeline_claude.csv")
TRUNC = 2000

ALIAS = REPO_ALIASES
FLEET_BASENAME = "-" + ROOT.strip("/").replace("/", "-")  # e.g. -Users-x-workspaces-aihero

# $ per million input tokens, matched by substring in order (so "opus-5-5" must precede
# "opus-5"); estimate_cost applies the standard output and cache multipliers to it.
IN_PRICE = {"opus-5-5": 4, "opus-5": 5, "opus-4": 5, "sonnet": 2, "fable": 10, "haiku": 1}
DEFAULT_PRICE = 5
UNPRICED = set()
BAD_LINES = collections.Counter()


def price_per_m(model):
    for k, v in IN_PRICE.items():
        if k in (model or ""):
            return v
    UNPRICED.add(model or "(none)")
    return DEFAULT_PRICE


def loads_line(line, source):
    """json.loads, or None counted under BAD_LINES[source] when the line won't parse."""
    try:
        return json.loads(line)
    except Exception:
        BAD_LINES[source] += 1
        return None


def estimate_cost(inp, out, cache_r, cache_w, model):
    return (inp + 1.25 * cache_w + 0.1 * cache_r + 5 * out) * price_per_m(model) / 1e6


def sha(s):
    return hashlib.sha256((s or "").encode()).hexdigest()[:16]


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
    return ""


_PLUGIN_NAMES = {PLUGIN_REPO_NAME} | {old for old, new in ALIAS.items() if new == PLUGIN_REPO_NAME}


def repo_of_projdir(base):
    if base == FLEET_BASENAME:
        return "fleet"
    if any(f"-claude-plugins-{name}" in base for name in _PLUGIN_NAMES):
        return PLUGIN_REPO_NAME
    if not base.startswith(FLEET_BASENAME + "-"):
        return None
    rest = base[len(FLEET_BASENAME) + 1:].split("--claude-worktrees-")[0]
    name = ALIAS.get(rest, rest)
    return name if name in ALL_REPOS else None


def repo_of_path(p):
    p = (p or "").rstrip("/")
    if p == ROOT:
        return "fleet"
    if "/.claude/plugins/" in p:
        return PLUGIN_REPO_NAME
    if p.startswith(ROOT + "/"):
        rest = p[len(ROOT) + 1:].split("/")[0]
        name = ALIAS.get(rest, rest)
        return name if name in ALL_REPOS else None
    return None


REJECT_RX = re.compile(r"doesn't want to proceed|permission.*denied|denied.*permission", re.I)
LIMIT_RX = re.compile(r"hit your (session|weekly|org's monthly spend) limit|limit reached", re.I)


def limit_kind(text):
    t = text.lower()
    if "monthly spend limit" in t:
        return "spend"
    if "session limit" in t:
        return "session"
    if "weekly limit" in t:
        return "weekly"
    if "credit" in t:
        return "credits"
    return "other"


def open_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    con.executescript("""
    CREATE TABLE sessions (
        session_id_hash TEXT PRIMARY KEY, repo TEXT, org TEXT,
        first_ts TEXT, last_ts TEXT, day TEXT, week TEXT, month TEXT,
        cc_version TEXT, main_model TEXT, git_branches TEXT,
        user_turns INTEGER, assistant_turns INTEGER, tool_calls INTEGER, subagent_count INTEGER,
        input_tokens INTEGER, output_tokens INTEGER, cache_read_tokens INTEGER, cache_write_tokens INTEGER,
        cost_usd REAL, cost_method TEXT, interrupted_count INTEGER, limit_messages INTEGER, pr_links TEXT
    );
    CREATE TABLE turns (
        session_id_hash TEXT, idx INTEGER, ts TEXT, role TEXT, model TEXT, branch TEXT,
        input_tokens INTEGER, output_tokens INTEGER, cache_read_tokens INTEGER, cache_write_tokens INTEGER,
        is_synthetic INTEGER, text_redacted TEXT
    );
    CREATE TABLE tool_calls (
        session_id_hash TEXT, ts TEXT, tool TEXT, subagent_type TEXT, model_override TEXT,
        is_error INTEGER, was_rejected INTEGER, question_count INTEGER, skill_name TEXT
    );
    CREATE TABLE asks (
        session_id_hash TEXT, ts TEXT, question_redacted TEXT, options_json TEXT, answer_redacted TEXT
    );
    CREATE TABLE subagent_runs (
        session_id_hash TEXT, agent_id_hash TEXT, ts_start TEXT, ts_end TEXT,
        subagent_type TEXT, model TEXT, input_tokens INTEGER, output_tokens INTEGER,
        cost_usd_est REAL, tool_calls INTEGER
    );
    CREATE TABLE limit_events (
        session_id_hash TEXT, ts TEXT, kind TEXT, org TEXT
    );
    CREATE TABLE prompts (
        ts TEXT, day TEXT, week TEXT, month TEXT, repo TEXT,
        text_redacted TEXT, chars INTEGER, is_slash_command INTEGER, command TEXT
    );
    CREATE TABLE memories (
        repo TEXT, file TEXT, name TEXT, type TEXT, created_ts TEXT, chars INTEGER,
        has_why INTEGER, links_json TEXT
    );
    CREATE TABLE model_releases (date TEXT, kind TEXT, name TEXT, notes TEXT);
    CREATE TABLE cc_releases (date TEXT, kind TEXT, name TEXT, notes TEXT);
    CREATE TABLE meta (source TEXT, path TEXT, rows INTEGER, extracted_at TEXT);
    """)
    return con


# ---------- orgs: label by first-seen order, never store the uuid ----------
org_labels = {}
org_order = []


def org_label(uuid):
    if not uuid:
        return None
    if uuid not in org_labels:
        org_labels[uuid] = chr(ord("A") + len(org_order))
        org_order.append(uuid)
    return org_labels[uuid]


# ---------- sessions ----------
def process_session_file(fpath, repo):
    session_id = os.path.basename(fpath)[:-6]
    sid_hash = sha(session_id)

    lines = []
    with open(fpath, errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            j = loads_line(line, "session")
            if j is not None:
                lines.append(j)
    if not lines:
        return None

    # pass 1: tool_results by tool_use_id, and org uuid
    tool_results = {}
    org_uuid = None
    for j in lines:
        if j.get("type") == "bridge-session" and j.get("ownerOrganizationUuid"):
            org_uuid = j["ownerOrganizationUuid"]
        if j.get("type") == "user":
            content = (j.get("message") or {}).get("content")
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_result":
                        body = c.get("content")
                        body_text = body if isinstance(body, str) else text_of(body)
                        tool_results[c.get("tool_use_id")] = {"is_error": bool(c.get("is_error")), "text": body_text or ""}

    versions = collections.Counter()
    branches = set()
    models = collections.Counter()
    pr_links = set()
    interrupted = 0
    limit_msgs = 0
    limit_rows = []
    turns_rows = []
    tool_call_rows = []
    ask_rows = []
    agent_invocations = {}  # agent_id -> {subagent_type, model_override, tool_use_id}
    first_ts = last_ts = None
    user_turns = assistant_turns = 0
    tot_in = tot_out = tot_cr = tot_cw = 0
    cost_state = None
    idx = 0

    for j in lines:
        ts = j.get("timestamp")
        if ts:
            first_ts = ts if not first_ts or ts < first_ts else first_ts
            last_ts = ts if not last_ts or ts > last_ts else last_ts
        if j.get("version"):
            versions[j["version"]] += 1
        if j.get("gitBranch"):
            branches.add(j["gitBranch"])
        if j.get("type") == "pr-link":
            pr_links.add(f'{j.get("prRepository")}#{j.get("prNumber")}')
        if j.get("type") == "cost-state":
            cost_state = j

        if j.get("type") == "assistant" and not j.get("isSidechain"):
            m = j.get("message") or {}
            model = m.get("model")
            u = m.get("usage") or {}
            is_synth = model == "<synthetic>"
            in_t, out_t, cr_t, cw_t = (u.get("input_tokens") or 0, u.get("output_tokens") or 0,
                                        u.get("cache_read_input_tokens") or 0, u.get("cache_creation_input_tokens") or 0)
            if not is_synth:
                models[model] += 1
                tot_in += in_t; tot_out += out_t; tot_cr += cr_t; tot_cw += cw_t
            assistant_turns += 1
            text = text_of(m.get("content"))
            turns_rows.append((sid_hash, idx, ts, "assistant", model, j.get("gitBranch"),
                                in_t, out_t, cr_t, cw_t, int(is_synth), redact(text)[:TRUNC]))
            idx += 1
            if is_synth and text and LIMIT_RX.search(text):
                limit_msgs += 1
                limit_rows.append((sid_hash, ts, limit_kind(text)))
            for c in m.get("content") or []:
                if not (isinstance(c, dict) and c.get("type") == "tool_use"):
                    continue
                name = c.get("name")
                inp = c.get("input") or {}
                tr = tool_results.get(c.get("id"), {})
                is_error = tr.get("is_error", False)
                was_rejected = bool(is_error and REJECT_RX.search(tr.get("text", "") or ""))
                subagent_type = model_override = skill_name = None
                question_count = None
                if name in ("Agent", "Task"):
                    subagent_type = inp.get("subagent_type")
                    model_override = inp.get("model")
                    m2 = re.search(r"agentId:\s*([0-9a-f]+)", tr.get("text", "") or "")
                    if m2:
                        agent_invocations[m2.group(1)] = {"subagent_type": subagent_type, "model_override": model_override}
                elif name == "Skill":
                    skill_name = inp.get("skill")
                elif name == "AskUserQuestion":
                    question_count = len(inp.get("questions") or [])
                    qtext = " | ".join(q.get("question", "") for q in (inp.get("questions") or []))
                    options = [{"label": redact(o.get("label"))[:TRUNC], "description": redact(o.get("description"))[:TRUNC]}
                               for q in (inp.get("questions") or []) for o in (q.get("options") or [])]
                    answer = tr.get("text", "")
                    ask_rows.append((sid_hash, ts, redact(qtext)[:TRUNC], json.dumps(options), redact(answer)[:TRUNC]))
                tool_call_rows.append((sid_hash, ts, name, subagent_type, model_override,
                                        int(is_error), int(was_rejected), question_count, skill_name))

        elif j.get("type") == "user" and not j.get("isSidechain"):
            m = j.get("message") or {}
            content = m.get("content")
            if isinstance(content, list) and any(isinstance(c, dict) and c.get("type") == "tool_result" for c in content):
                continue
            txt = text_of(content)
            if "[Request interrupted by user" in txt:
                interrupted += 1
                continue
            if j.get("isMeta"):
                continue
            origin_kind = (j.get("origin") or {}).get("kind")
            if origin_kind not in (None, "human"):
                continue
            if txt.startswith("<local-command") or txt.startswith("<task-notification"):
                continue
            user_turns += 1
            turns_rows.append((sid_hash, idx, ts, "user", None, j.get("gitBranch"), 0, 0, 0, 0, 0, redact(txt)[:TRUNC]))
            idx += 1

    if not first_ts:
        return None

    cc_version = versions.most_common(1)[0][0] if versions else None
    main_model = models.most_common(1)[0][0] if models else None
    org = org_label(org_uuid)
    d = dims(first_ts)

    if cost_state and cost_state.get("totalCostUSD") is not None:
        cost_usd = cost_state["totalCostUSD"]
        cost_method = "cost-state"
        mu = cost_state.get("modelUsage") or {}
        if mu:
            tot_in = sum(v.get("inputTokens") or 0 for v in mu.values())
            tot_out = sum((v.get("outputTokens") or 0) for v in mu.values())
            tot_cr = sum(v.get("cacheReadInputTokens") or 0 for v in mu.values())
            tot_cw = sum(v.get("cacheCreationInputTokens") or 0 for v in mu.values())
    else:
        cost_usd = estimate_cost(tot_in, tot_out, tot_cr, tot_cw, main_model)
        cost_method = "priced"

    # subagent transcripts live beside this session file: <session>/subagents/*.jsonl
    subdir = os.path.join(os.path.dirname(fpath), session_id, "subagents")
    subagent_rows = []
    for spath in glob.glob(os.path.join(subdir, "*.jsonl")):
        row = process_subagent_file(spath, sid_hash, agent_invocations)
        if row:
            subagent_rows.append(row)

    session_row = (sid_hash, repo, org, first_ts, last_ts, d["day"], d["week"], d["month"],
                   cc_version, main_model, json.dumps(sorted(branches)),
                   user_turns, assistant_turns, len(tool_call_rows), len(subagent_rows),
                   tot_in, tot_out, tot_cr, tot_cw, cost_usd, cost_method,
                   interrupted, limit_msgs, json.dumps(sorted(pr_links)))
    return session_row, turns_rows, tool_call_rows, ask_rows, subagent_rows, limit_rows


def process_subagent_file(spath, sid_hash, agent_invocations):
    m = re.search(r"agent-([0-9a-f]+)\.jsonl$", os.path.basename(spath))
    if not m:
        return None
    agent_id = m.group(1)
    inv = agent_invocations.get(agent_id, {})
    first_ts = last_ts = None
    models = collections.Counter()
    tot_in = tot_out = tot_cr = tot_cw = 0
    tool_calls = 0
    with open(spath, errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            j = loads_line(line, "subagent")
            if j is None:
                continue
            ts = j.get("timestamp")
            if ts:
                first_ts = ts if not first_ts or ts < first_ts else first_ts
                last_ts = ts if not last_ts or ts > last_ts else last_ts
            if j.get("type") != "assistant":
                continue
            m2 = j.get("message") or {}
            model = m2.get("model")
            if model and model != "<synthetic>":
                models[model] += 1
                u = m2.get("usage") or {}
                tot_in += u.get("input_tokens") or 0
                tot_out += u.get("output_tokens") or 0
                tot_cr += u.get("cache_read_input_tokens") or 0
                tot_cw += u.get("cache_creation_input_tokens") or 0
            for c in m2.get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    tool_calls += 1
    if not first_ts:
        return None
    actual_model = models.most_common(1)[0][0] if models else inv.get("model_override")
    cost_est = estimate_cost(tot_in, tot_out, tot_cr, tot_cw, actual_model)
    return (sid_hash, sha(agent_id), first_ts, last_ts, inv.get("subagent_type"), actual_model,
            tot_in, tot_out, cost_est, tool_calls)


# ---------- prompts (history.jsonl) ----------
def ingest_prompts(con):
    rows = []
    path = os.path.join(HOME, ".claude", "history.jsonl")
    with open(path, errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            j = loads_line(line, "history")
            if j is None:
                continue
            t = j.get("timestamp")
            if not t:
                continue
            repo = repo_of_path(j.get("project"))
            if not repo:
                continue
            ts = dt.datetime.fromtimestamp(t / 1000, tz=dt.timezone.utc)
            d = dims(ts)
            txt = (j.get("display") or "").strip()
            slash = re.match(r"^/([\w:.-]+)", txt)
            rows.append((d["ts"], d["day"], d["week"], d["month"], repo, redact(txt)[:TRUNC], len(txt),
                         int(bool(slash)), slash.group(1) if slash else None))
    con.executemany("INSERT INTO prompts VALUES (?,?,?,?,?,?,?,?,?)", rows)
    return path, len(rows)


# ---------- memories ----------
def ingest_memories(con):
    rows = []
    n = 0
    for d in glob.glob(os.path.join(HOME, ".claude", "projects", "*")):
        repo = repo_of_projdir(os.path.basename(d))
        if not repo:
            continue
        for f in glob.glob(os.path.join(d, "memory", "*.md")):
            try:
                raw = open(f, errors="replace").read()
            except Exception:
                continue
            fm = {}
            m = re.match(r"^---\n(.*?)\n---\n?(.*)$", raw, re.S)
            body = raw
            if m:
                body = m.group(2)
                for line in m.group(1).splitlines():
                    mm = re.match(r"^([a-zA-Z]+):\s*(.*)$", line)
                    if mm:
                        fm[mm.group(1)] = mm.group(2).strip()
            try:
                created_ts = dt.datetime.fromtimestamp(os.path.getctime(f), tz=dt.timezone.utc).isoformat()
            except Exception:
                created_ts = None
            links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", body)
            rows.append((repo, os.path.basename(f), fm.get("name"), fm.get("type"), created_ts,
                         len(raw), int("**Why:**" in body or "**Why**:" in body), json.dumps(links)))
            n += 1
    con.executemany("INSERT INTO memories VALUES (?,?,?,?,?,?,?,?)", rows)
    return n


# ---------- timeline ----------
def ingest_timeline(con):
    if not os.path.exists(TIMELINE_CSV):
        return 0, 0
    import csv
    model_rows, cc_rows = [], []
    with open(TIMELINE_CSV, newline="") as fh:
        for row in csv.DictReader(fh):
            date, kind, name, notes = row.get("date"), row.get("kind"), row.get("label"), row.get("detail")
            if kind == "model":
                model_rows.append((date, kind, name, notes))
            elif kind == "claude-code":
                cc_rows.append((date, kind, name, notes))
    con.executemany("INSERT INTO model_releases VALUES (?,?,?,?)", model_rows)
    con.executemany("INSERT INTO cc_releases VALUES (?,?,?,?)", cc_rows)
    return len(model_rows), len(cc_rows)


def main():
    t0 = time.time()
    con = open_db()

    n_sessions = n_turns = n_tools = n_asks = n_subagents = n_limits = 0
    earliest_transcript = None
    total_cost = 0.0
    total_tokens = 0

    for d in sorted(glob.glob(os.path.join(HOME, ".claude", "projects", "*"))):
        base = os.path.basename(d)
        repo = repo_of_projdir(base)
        if not repo:
            continue
        for fpath in sorted(glob.glob(os.path.join(d, "*.jsonl"))):
            result = process_session_file(fpath, repo)
            if not result:
                continue
            session_row, turns_rows, tool_call_rows, ask_rows, subagent_rows, limit_rows = result
            con.execute("INSERT INTO sessions VALUES (" + ",".join("?" * 24) + ")", session_row)
            con.executemany("INSERT INTO turns VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", turns_rows)
            con.executemany("INSERT INTO tool_calls VALUES (?,?,?,?,?,?,?,?,?)", tool_call_rows)
            con.executemany("INSERT INTO asks VALUES (?,?,?,?,?)", ask_rows)
            con.executemany("INSERT INTO subagent_runs VALUES (?,?,?,?,?,?,?,?,?,?)", subagent_rows)
            con.executemany("INSERT INTO limit_events VALUES (?,?,?,?)",
                             [(sid, ts, kind, session_row[2]) for sid, ts, kind in limit_rows])
            n_sessions += 1
            n_turns += len(turns_rows)
            n_tools += len(tool_call_rows)
            n_asks += len(ask_rows)
            n_subagents += len(subagent_rows)
            n_limits += len(limit_rows)
            total_cost += session_row[19] or 0
            total_tokens += (session_row[15] or 0) + (session_row[16] or 0) + (session_row[17] or 0) + (session_row[18] or 0)
            ft = session_row[3]
            if ft and (not earliest_transcript or ft < earliest_transcript):
                earliest_transcript = ft

    prompts_path, n_prompts = ingest_prompts(con)
    n_memories = ingest_memories(con)
    n_model_rel, n_cc_rel = ingest_timeline(con)

    con.execute("INSERT INTO meta VALUES (?,?,?,?)",
                ("earliest_transcript_before_deletion_cutoff", "2026-08-20", 0,
                 dt.datetime.now(dt.timezone.utc).isoformat()))
    con.execute("INSERT INTO meta VALUES (?,?,?,?)",
                ("earliest_transcript_seen", earliest_transcript, n_sessions,
                 dt.datetime.now(dt.timezone.utc).isoformat()))
    con.execute("INSERT INTO meta VALUES (?,?,?,?)",
                ("sessions", os.path.join(HOME, ".claude", "projects"), n_sessions,
                 dt.datetime.now(dt.timezone.utc).isoformat()))
    con.execute("INSERT INTO meta VALUES (?,?,?,?)",
                ("prompts", prompts_path, n_prompts, dt.datetime.now(dt.timezone.utc).isoformat()))
    con.execute("INSERT INTO meta VALUES (?,?,?,?)",
                ("memories", os.path.join(HOME, ".claude", "projects", "*", "memory"), n_memories,
                 dt.datetime.now(dt.timezone.utc).isoformat()))
    con.execute("INSERT INTO meta VALUES (?,?,?,?)",
                ("timeline", TIMELINE_CSV, n_model_rel + n_cc_rel, dt.datetime.now(dt.timezone.utc).isoformat()))
    con.execute("INSERT INTO meta VALUES (?,?,?,?)",
                ("org_labels", "count", len(org_order), dt.datetime.now(dt.timezone.utc).isoformat()))
    con.commit()
    con.close()

    elapsed = time.time() - t0
    print(f"sessions {n_sessions}  turns {n_turns}  tool_calls {n_tools}  asks {n_asks}  "
          f"subagent_runs {n_subagents}  limit_events {n_limits}  prompts {n_prompts}  "
          f"memories {n_memories}  model_releases {n_model_rel}  cc_releases {n_cc_rel}  "
          f"total_cost ${total_cost:,.2f}  total_tokens {total_tokens:,}  "
          f"earliest_transcript {earliest_transcript}  elapsed {elapsed:.1f}s")
    if BAD_LINES:
        print(f"  ! unparsable transcript lines skipped: {sum(BAD_LINES.values())} "
              f"({', '.join(f'{k} {v}' for k, v in sorted(BAD_LINES.items()))})", file=sys.stderr)
    if UNPRICED:
        print(f"  ! {len(UNPRICED)} models with no known price, estimated at ${DEFAULT_PRICE}/M input: "
              f"{', '.join(sorted(UNPRICED))}", file=sys.stderr)


if __name__ == "__main__":
    main()
