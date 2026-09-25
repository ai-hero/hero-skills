"""Review comments tagged for security -> detectors.sqlite, table review_topics.

Each non-empty review body (first 700 characters) goes to Haiku, batched:
is it about security, how severe is the worst finding it raises, and a
short summary. Cached by sha256(state + body) in review_topics_cache.
"""
import hashlib, json, os, sqlite3, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import d1_changesets as D1
from ingest.fleet import OUT

DB_PATH = os.path.join(OUT, "detectors.sqlite")
BATCH = 30
SNIP = 700
HEADER = """You read code-review comments. For each one decide:
- security: true if it raises or discusses a security issue (auth, secrets, injection, access
  control, crypto, supply chain, data exposure), else false;
- severity: the worst finding it raises -- "critical", "high", "medium", "low" or "none";
- summary: at most 12 words.
A review that approves with no findings is severity "none".

Reply with ONLY a JSON object, no prose, no fence:
{"<id>": {"security": true|false, "severity": "...", "summary": "..."}, ...}

Reviews:
"""


def build():
    gh = sqlite3.connect(os.path.join(OUT, "github.sqlite"))
    d = sqlite3.connect(DB_PATH)
    d.execute("CREATE TABLE IF NOT EXISTS review_topics_cache (h TEXT PRIMARY KEY, security INTEGER, severity TEXT, summary TEXT)")
    reviews = gh.execute("SELECT repo, number, reviewer, reviewer_is_bot, state, body_redacted FROM pr_reviews "
                         "WHERE LENGTH(TRIM(body_redacted)) > 20").fetchall()
    key = lambda r: hashlib.sha256(f"{r[4]}\n{r[5]}".encode()).hexdigest()
    cached = {r[0] for r in d.execute("SELECT h FROM review_topics_cache")}
    todo = list({key(r): r for r in reviews if key(r) not in cached}.items())
    print(f"{len(reviews)} reviews, {len(todo)} to tag", file=sys.stderr)
    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    total = 0.0
    with ThreadPoolExecutor(max_workers=D1.WORKERS) as pool:
        futs = {pool.submit(D1.call_haiku, [f"--- id={j} ({r[4]}) ---\n{r[5].strip()[:SNIP]}" for j, (_, r) in enumerate(b)],
                            header=HEADER): b for b in batches}
        for n, fut in enumerate(as_completed(futs), 1):
            b = futs[fut]
            reply, cost = fut.result()
            total += cost
            for j, (h, r) in enumerate(b):
                t = reply.get(str(j)) if isinstance(reply, dict) else None
                if isinstance(t, dict):
                    d.execute("INSERT OR REPLACE INTO review_topics_cache VALUES (?,?,?,?)",
                              (h, int(bool(t.get("security"))), str(t.get("severity", "none")), str(t.get("summary", ""))[:200]))
            d.commit()
            print(f"  batch {n}/{len(batches)} ${total:.2f}", file=sys.stderr)
    d.execute("DROP TABLE IF EXISTS review_topics")
    d.execute("CREATE TABLE review_topics (repo TEXT, number INTEGER, reviewer TEXT, reviewer_is_bot INTEGER, "
              "state TEXT, security INTEGER, severity TEXT, summary TEXT)")
    tags = {r[0]: r[1:] for r in d.execute("SELECT * FROM review_topics_cache")}
    for r in reviews:
        if key(r) in tags:
            d.execute("INSERT INTO review_topics VALUES (?,?,?,?,?,?,?,?)", (*r[:5], *tags[key(r)]))
    d.commit()
    print(f"review_topics: {d.execute('SELECT COUNT(*), SUM(security) FROM review_topics').fetchone()}, ${total:.2f}")


if __name__ == "__main__":
    build()
