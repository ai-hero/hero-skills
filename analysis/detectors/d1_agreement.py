"""Second rater for D1 -> detectors.sqlite, table cs_agreement.

Re-groups a month-stratified sample of multi-commit PRs with a stronger model
(same prompt, same unit text) and compares it with D1's grouping: whether the
change-set counts match, and pair agreement -- for every pair of commits in a
PR, whether both raters put them in the same change set or both kept them apart.
"""
import itertools, json, os, random, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import d1_changesets as D1
from cube.db import connect

PER_MONTH = 20
MODEL = "sonnet"


def together(sets, n):
    return {(i, j): any(i in idx and j in idx for _, idx in sets) for i, j in itertools.combinations(range(n), 2)}


def build():
    con = connect()
    d = sqlite3.connect(D1.DB_PATH)
    cache = {h: json.loads(s) for h, s in d.execute("SELECT unit_hash, sets_json FROM cs_cache")}
    month = {(r[0], r[1]): r[2] for r in con.execute("SELECT repo, sha, month FROM git.commits")}
    pool = {}
    for u in D1.load_units(con):
        key, repo, kind, uid, main_sha, header, commits, rule = u
        h = D1.sha256(D1.PROMPT_VERSION + D1.unit_text(key, header, commits))
        if kind == "pr" and not rule and len(commits) >= 2 and h in cache:
            pool.setdefault(month.get((repo, main_sha)), []).append((u, cache[h]))
    rnd = random.Random(11)
    sample = [x for m in sorted(k for k in pool if k) for x in rnd.sample(pool[m], min(PER_MONTH, len(pool[m])))]
    print(f"{len(sample)} PRs sampled across {len(pool)} months", file=sys.stderr)
    d.execute("DROP TABLE IF EXISTS cs_agreement")
    d.execute("CREATE TABLE cs_agreement (repo TEXT, unit_id TEXT, month TEXT, n_commits INTEGER, "
              "n_a INTEGER, n_b INTEGER, pair_agreement REAL, sets_b TEXT)")
    from concurrent.futures import ThreadPoolExecutor
    chunks = [sample[i:i + 6] for i in range(0, len(sample), 6)]
    total = 0.0
    with ThreadPoolExecutor(max_workers=D1.WORKERS) as pool:
        results = pool.map(lambda c: D1.call_haiku([D1.unit_text(u[0], u[5], u[6]) for u, _ in c], model=MODEL), chunks)
        for chunk, (reply, cost) in zip(chunks, results):
            total += cost
            for u, a in chunk:
                b = D1.clean_sets(reply.get(u[0]), len(u[6]))
                if not b:
                    continue
                n = len(u[6])
                ta, tb = together(a, n), together(b, n)
                agree = sum(ta[k] == tb[k] for k in ta) / len(ta)
                d.execute("INSERT INTO cs_agreement VALUES (?,?,?,?,?,?,?,?)",
                          (u[1], u[3], month.get((u[1], u[4])), n, len(a), len(b), round(agree, 3), json.dumps(b)))
            d.commit()
    print(f"cs_agreement: {d.execute('SELECT COUNT(*) FROM cs_agreement').fetchone()[0]} PRs, ${total:.2f}")

if __name__ == "__main__":
    build()
