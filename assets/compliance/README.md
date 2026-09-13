# Compliance register — the baseline

`scripts/audit.py` computes (check × repo) results from a register with two
halves:

| Half | Where | Holds |
| --- | --- | --- |
| baseline | this directory, shipped with the plugin | controls and checks any repo on this workflow is held to; generic rationale only |
| overlay | the fleet's register checkout — FLEET.md `register:`, default `.fleet/` | `reference:` per control and check, `known_violations`, `applies_to_groups`, the fleet's incident history, and any controls or checks of its own |

Merged by id, overlay fields winning. Outside a fleet only the baseline
applies and the family is the current repo. Results are never stored: a
stored result is a copy, and copies drift. `scripts/consistency.py` writes
the fleet's human table into the register checkout, never here.

Unlike the other assets, nothing here is installed into a repo. A repo that
carries a copy of the register fails REG-01.
