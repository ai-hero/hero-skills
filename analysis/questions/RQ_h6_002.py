"""Q10.xx / RQ-h6-002 -- When several clones need the same capability, is it
built once in the template and inherited, or built separately in each
clone? D7-backed (detectors.duplicate_fixes): a cluster spanning >=2 clones
with no template commit in it is evidence of separate builds; a cluster
that includes the template is evidence of build-once-and-inherit (though
D3, not D7, is the detector that actually confirms inheritance vs
coincidence -- this only flags the candidate clusters).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import TEMPLATE_REPO

RQ_ID = "RQ-h6-002"
QUESTION = "When several clones need the same capability, is it built once and inherited, or built separately in each?"

SQL = """
SELECT cluster_id, signature, GROUP_CONCAT(DISTINCT repo) AS repos, COUNT(*) AS commits
FROM detectors.duplicate_fixes
GROUP BY cluster_id
ORDER BY commits DESC
"""


def answer(con):
    if not TEMPLATE_REPO:
        return [{"note": "no FLEET.md group: template repo in this fleet"}]
    rows = con.execute(SQL).fetchall()
    out = []
    template_involved = 0
    for r in rows:
        repos = r["repos"].split(",")
        has_template = TEMPLATE_REPO in repos
        template_involved += has_template
        out.append({"cluster_id": r["cluster_id"], "signature": r["signature"][:60],
                     "repos": repos, "includes_template": has_template})
    out.insert(0, {"summary": f"{len(rows)} cross-repo duplicate clusters, "
                               f"{template_involved} include {TEMPLATE_REPO} (build-once candidate), "
                               f"{len(rows) - template_involved} look like separate builds"})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
