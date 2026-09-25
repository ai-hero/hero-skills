-- Shared views. Each block declares the attached sources it reads; blocks whose sources are missing are skipped.

-- needs: git
CREATE TEMP VIEW v_commits AS
SELECT c.*, r.role, CASE WHEN c.is_bot = 1 THEN 'bot' WHEN c.claude_trailer = 1 THEN 'agent' ELSE 'human' END AS actor
FROM git.commits c JOIN git.repos r USING (repo);

-- needs: plans
CREATE TEMP VIEW v_items AS
SELECT i.*, CASE WHEN EXISTS (SELECT 1 FROM plans.item_edges e WHERE e.repo = i.repo AND e.src_item = i.item_id AND e.kind = 'discovered_from')
                 THEN 1 ELSE 0 END AS is_found_work
FROM plans.plan_items i;

-- needs: detectors
-- D10 presence scanner: does <artifact> exist in <repo> at <snapshot>.
CREATE TEMP VIEW v_presence AS
SELECT * FROM detectors.presence;
