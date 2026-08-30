# The recalibrate verb

Sixteen skills accept `recalibrate`: ask me the questions that decide how this
skill works, and write the answers. `scripts/hero-fields.sh` holds the map of
which skill reads which fields, and `scripts/hero-fields.test.sh` ties the map
and the skills to each other in both directions — a skill declaring the verb
with no rows, or rows with no skill, fails the suite.

## The principle

A skill misbehaves for one of two reasons: the skill is wrong, or the config
that drives it is wrong. The second is far more common and much cheaper to
fix — and the moment you notice is the moment you know which field is wrong.

`recalibrate` puts the fix where the noticing happens. You do not re-run a
repo-wide investigation because `ship-pr` merged with the wrong strategy; you
run `hero-skills:ship-pr recalibrate`, which asks about the eight fields
`ship-pr` reads across Repository, CI/CD and Deployment — and nothing else.

Three properties make it safe to reach for:

1. **It is scoped.** A skill asks about the fields *it* reads and nothing
   else. Whole-file convergence is `hero-skills:init-hero recalibrate` — one
   skill's job, not every skill's.
2. **It never does the work.** `recalibrate` ends when the config is written.
   It does not then push, merge, refactor, or plan. The user decides whether
   the recalibrated skill runs, and runs it themselves.
3. **It writes only what the user confirmed.** Every proposal is shown with
   its evidence and its current value beside it. Silence is not consent, and
   a field the user did not speak to keeps the value it had.

## Recalibrate is not sync

`recalibrate` changes `HERO.md` — the configuration that decides *how* a skill
does its work. It is not how the work itself gets planned or converged, and it
never touches the files those skills keep:

| Verb | File | What it means |
| --- | --- | --- |
| `recalibrate` | `HERO.md` | how this skill should behave |
| `architecture sync` | `DESIGN.md` | converge the design record with the codebase |
| `fleet sync` | `FLEET.md` | converge the map with the folder beside it |
| `wayfare sync` | `.plans/` | converge the plan with the design |

`architecture` has both: `sync` for `DESIGN.md`, `recalibrate` for the three
`HERO.md` fields that tell it how to run.

Three skills read `HERO.md` and deliberately have no `recalibrate`. `fleet`
runs at the fleet root, where there is no `HERO.md` to recalibrate.
`audit-plugin` reads the file as the *subject* of its audit rather than as its
own config. `think-it-through` is a dialogue with the user, and stopping it to
ask about config fields is the interruption the verb exists to avoid —
recalibrate the skill that acts on its output instead.

`hero-skills:init-hero recalibrate` is the whole-file pass, and the only one.
It replaced `init-hero --update`; every other skill's `recalibrate` is a
scoped slice of the same motion. `init-hero` is also the one mapped skill that
does not call `hero-fields.sh`: it re-investigates the repo rather than
reading a field table.

## The procedure

Four phases, in this order, in every skill.

1. **Report.** Print the fields this skill reads, their current values, and
   what each one decides for this skill — `scripts/hero-fields.sh SKILL` is
   that table. Anything in parentheses is a finding rather than a value:
   `(unset)`, `(no-section)`, `(refused)`, `(no-file)`, and `(absent)` for a
   missing section. Then look at the repo for those rows — a field the tree
   can answer should reach the user as a proposal with its evidence, not as an
   open question. `(no-file)` on every row is not a recalibrate at all: send
   the user to `hero-skills:init-hero`.
2. **Ask.** One numbered list, every question at once. Each question carries
   the evidence behind the proposal and the value it would replace. Never
   ask in freeform prose, and never ask about a field that already holds the
   right value.
3. **Write.** Only the confirmed answers, only into the sections this skill
   reads. Leave the rest of `HERO.md` untouched — a scoped verb that rewrites
   a whole file is a whole-file verb wearing a disguise.
4. **Commit.** Config is a tracked artifact; stage and commit it without
   asking. Do not open a PR, and do not push.

Then stop and say what changed. The next line the user reads is what to run
now that the config is right — not the output of having run it.

## Anti-patterns

- **Running the skill afterwards.** `recalibrate` is a recommendation, not a
  retry. Chaining into the real work hides which change fixed the behavior
  and spends a merge or a push on a config guess.
- **Asking about fields the skill does not read.** The scope is the whole
  point. Send the rest to `hero-skills:init-hero recalibrate`.
- **Rewriting the file to normalize it.** Reformatting unrelated sections
  turns a four-line config change into a diff nobody reviews.
- **Reaching for it when the answer is `sync`.** A stale `DESIGN.md`, a
  `FLEET.md` row for a repo that moved, a plan that no longer matches the
  design — none of those are configuration, and no `HERO.md` field fixes
  them.
- **Inventing an answer for an absent field.** A field the investigation
  could not resolve is a question, not a default. Writing the guess is how a
  wrong value becomes permanent — nobody re-confirms a field that looks set.
