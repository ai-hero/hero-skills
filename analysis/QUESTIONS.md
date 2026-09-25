# Research questions

The questions the software-factory study asks, by chapter. Each chapter's `report/chNN/data.py`
computes the answers against the local data under `.analysis/`; the answers themselves are not
published here.

## Chapter 1 · Introduction (front matter)

- **Q 1.01** Which repos make up the fleet, what is each one for, and when did each come alive?
- **Q 1.02** How many repos did the owner keep moving at once, week by week?
- **Q 1.03** How many different repos did the owner touch in a single day?
- **Q 1.04** How much work has the fleet shipped, counted in change sets, and how did the weekly rate grow?
- **Q 1.05** Where did the work go: which apps got the most, and did the mix shift?
- **Q 1.06** How much of the work built the apps, and how much built the factory itself?
- **Q 1.07** How large has the codebase grown, repo by repo?
- **Q 1.08** What does a week of the factory cost, in model spend and in the owner's hours?
- **Q 1.09** What kind of work is it: features, fixes, or upkeep?
- **Q 1.10** What does one change set look like, and how does it roll up into PRs, work items and goals?
- **Q 1.11** How much of the work was planned in writing before it was built?
- **Q 1.12** How did the factory's own toolkit grow: skills, gates and practices, and when did each land?
- **Q 1.13** How quickly did each practice reach the rest of the fleet after it landed in wayfare?
- **Q 1.14** Which of the study's themes does the fleet's work fall under, and how has that shifted?

## Chapter 2 · Research setting, method and the baseline

- **Q 2.01** How do change sets link to work items, and work items to goals?
- **Q 2.02** What did each repo have when its work happened: skills, work items, goals, messages?
- **Q 2.03** When was each repo actively developed?
- **Q 2.04** How stale does each app's DESIGN.md get, and does anything catch it?
- **Q 2.05** Which process changes were made to save cost or time, and can we see their effect?
- **Q 2.06** How has the work-item format changed, and which repos still run an old one?
- **Q 2.07** Did commit messages change as the factory evolved?
- **Q 2.08** Did change sets get smaller or larger as the factory evolved?
- **Q 2.09** How many change sets did the fleet ship per week, and at which stage?
- **Q 2.10** Who wrote the commits at each stage: human alone, agent, or bot?
- **Q 2.11** How far does a second rater agree with Haiku's change-set grouping?
- **Q 2.12** Can spend be tied to a change set or work item, and where does the chain break?
- **Q 2.13** How often do reviewers disagree, and do any disagreements concern security?
- **Q 2.14** How accurate are the links we infer: PR → work item, goal log → commit, session → PR?
- **Q 2.15** How different are the counts of the same history: commits on main, original commits, change sets?
- **Q 2.16** Who reviewed changes at each stage: nobody, a bot, or a human?
- **Q 2.17** How many commits make a change set, and how many change sets make a work item?
- **Q 2.18** How focused are PRs at each stage, in change sets per PR?
- **Q 2.19** How much of the work is observable: planned in a work item, logged in a session, or neither?
- **Q 2.20** Which factory changes can we credit with an effect, and on what evidence?
- **Q 2.21** How much does the ranking of apps change with the unit: lines, commits, PRs, change sets?
- **Q 2.22** How much rework is caught inside the PR, by a gate, or after merge?

## Chapter 3 · The harness

- **Q 3.01** Which model wrote the fleet's work each week, and how fast did each new model take over after its release?
- **Q 3.02** Is work done with one model followed by more fixes than work done with another?
- **Q 3.03** How many subagents does a session launch, of which kinds, and how has that changed?
- **Q 3.04** Does the main thread hand investigation to a subagent, as the instructions ask, and does its context stay small?
- **Q 3.05** How often does a session hit context compaction, and does the owner correct the agent more often after it?
- **Q 3.06** How often does work run in its own worktree rather than the shared checkout, and do sessions in a shared checkout collide?
- **Q 3.07** How often does the agent stop to ask the owner, as a question or a permission prompt, per hour of work?
- **Q 3.08** How long after Claude Code ships a feature does the fleet use it, and which features did it later drop?

## Chapter 4 · Human in the loop

- **Q 4.01** Where does the factory wait on the owner, and which of those waits leave a timestamped record?
- **Q 4.02** How much does the owner type into the factory each week, and how much per change set shipped?
- **Q 4.03** When is the owner at the keyboard, and does that time grow with the fleet?
- **Q 4.04** How many owner gates does a work item pass through, and how did the gate move as the factory matured?
- **Q 4.05** Does the owner mark work items ready in batches, and how long does an item wait for that mark?
- **Q 4.06** What share of shipped work had an owner decision behind it, and what share reached main with none?
- **Q 4.07** How long does work sit waiting on the owner, and what share of session time is that wait?
- **Q 4.08** How often does an agent stop to ask the owner something, what about, and at which phase?
- **Q 4.09** When the agent recommends an option, how often does the owner take it?
- **Q 4.10** How often does the owner correct or redirect an agent, and is that falling per change set?
- **Q 4.11** How often does the owner stop a running agent mid-task?
- **Q 4.12** How often does the owner deny a tool call, and did denials fall as permissions caught up with policy?
- **Q 4.13** Who actually reviews and approves merged work, once agents acting under the owner's account are told apart from the owner?
- **Q 4.14** Do one-way-door changes stop for a human, or merge like everything else?
- **Q 4.15** Is the owner the only human in the loop?

## Chapter 5 · Skills and factory evolution

- **Q 5.01** How has the set of skills grown, been renamed, merged and retired since the plugin started?
- **Q 5.02** How much work went into the factory itself each week, and of what kind?
- **Q 5.03** Did the skills' prose level off while scripts and tests grew?
- **Q 5.04** What share of each skill's steps runs as a script rather than as prose the model interprets?
- **Q 5.05** How often is each skill invoked each week, and which few carry the factory?
- **Q 5.06** How often does a skill run end cleanly, without an error, an interruption or the owner correcting it?
- **Q 5.07** Who starts each skill, the owner or an agent, and has that shifted?
- **Q 5.08** When one skill hands off to the next (push → review → ship), how often does the chain complete in one session?
- **Q 5.09** Which route does work take to a merge: a goal, a one-shot pipeline, pipeline skills by hand, or no skill at all?
- **Q 5.10** After a skill is renamed, how long does the owner keep typing the old name?
- **Q 5.11** How often does a change to the plugin need a follow-up fix, and how quickly is it fixed?
- **Q 5.12** Do the skills that give a verdict end with an explicit one, treat outside text as data, and cap their waits, and since when?
- **Q 5.13** What sets off a change to the plugin: the owner's feedback, a fleet repo's report, a review or audit, or planned work?
- **Q 5.14** Which repos use the skills, since when, and how often is the roadmap refresh run in each?
- **Q 5.15** How does each repo take the plugin, and what did the 22 Sep repo rename cost?
- **Q 5.16** Does each repo's HERO.md set every field the skills read?
- **Q 5.17** Which repos wrote skills of their own, and did any move up into the plugin?

## Chapter 6 · Connectors

- **Q 6.01** Which connections does each repo declare, in what form, and when did each first appear?
- **Q 6.02** Which connection kinds does a skill actually read, and how long did declared kinds sit with nothing reading them?
- **Q 6.03** How does the agent actually reach each connection, week by week, and does its use match what the repo declares?
- **Q 6.04** How often was a declared reach wrong, and how long did it stay wrong?
- **Q 6.05** How often is a connector's value copied into more than one place, and how long do the copies disagree?
- **Q 6.06** Once a repo's agent could read its design, did design work shift from owner-reported to agent-found?
- **Q 6.07** How far behind the design source does the design-system's snapshot sit, and does the gap shrink?
- **Q 6.08** How long does a design-system release take to reach each consuming repo?
- **Q 6.09** How much of each app's UI comes from the design-system registry rather than being written in the repo?
- **Q 6.10** How much open divergence between the design and the code does each repo carry, and who notices it first?
- **Q 6.11** When the code diverges from the design, how does it end: a fix, a recorded decision to diverge, a question back to the design, or nothing?
- **Q 6.12** How often does the code send findings back to the design source, and do they get answered?
- **Q 6.13** When a connection could not be reached in a session, did the run say so or quietly carry on without it?
- **Q 6.14** How often does work stop because a login or credential has expired, and how long does it wait for the owner?
- **Q 6.15** How many work items could only be verified by a person because the agent lacked access, and how long did they wait for that check?

## Chapter 7 · Knowledge and memory

- **Q 7.01** Which knowledge stores does each repo keep, and when did each one appear?
- **Q 7.02** How much instruction text does an agent load before it starts, and did moving detail on demand shrink it?
- **Q 7.03** How often does work correct prose that had gone false, and is the fix its own work or a rider on something else?
- **Q 7.04** What do agents write into a work item's log, and has it become a record of mistakes and decisions?
- **Q 7.05** How does agent memory grow, and what share of it says why and links to anything?
- **Q 7.06** Can the cost of a work item be read back from the plan store?
- **Q 7.07** Who writes the plan store: skills, agents outside a skill, or the owner?
- **Q 7.08** What can the factory observe about each repo without asking an agent?

## Chapter 8 · Architecture and design records

- **Q 8.01** When did each repo get a design record, and which repos still have none?
- **Q 8.02** How did the design records grow, and are they still being edited?
- **Q 8.03** How many decisions are recorded, and does the rate keep pace with the work?
- **Q 8.04** Are decisions written when they are made, or backfilled later?
- **Q 8.05** How much of each app's record is inherited from the template, and how fast do template decisions reach the clones?
- **Q 8.06** Where does fleet-level architecture live, and how much of it is restated per repo?
- **Q 8.07** Do records follow their own rule that decisions are append-only?
- **Q 8.08** How much work touches the design record, and which path writes it?
- **Q 8.09** How far behind the code is each record?
- **Q 8.10** Do all records carry the template's sections, and did the section set drift?
- **Q 8.11** Is each decision recorded in the same change that makes it?
- **Q 8.12** Do architectural work items cite the design record?
- **Q 8.13** Do facts stated in several places agree, and are they checked?
- **Q 8.14** Have the repos' own guardrails ever fired?

## Chapter 9 · Work items, flow and wall time

- **Q 9.01** How many work items are opened and closed each week, and is the backlog growing or draining?
- **Q 9.02** What kind of work do the items describe, and did the mix shift from features to structural work?
- **Q 9.03** Where does work come from: the roadmap, the owner, an audit, or something found while doing other work?
- **Q 9.04** How long does a work item take from filed to shipped, and did that get shorter as the factory evolved?
- **Q 9.05** How long does an item wait for the owner to mark it ready, and how long from ready to shipped?
- **Q 9.06** Once ready, how long do items wait to be picked up, and how long do blocked items wait after their dependency ships?
- **Q 9.07** Does security work ship faster than other work, and how much of the hardening audit has shipped?
- **Q 9.08** How does work end: shipped, delivered upstream, dropped, or still open?
- **Q 9.09** How many PRs does a work item take, and how many work items does one PR carry?
- **Q 9.10** How long does a goal take, how many items does it cover, and how often does its scope grow after it starts?
- **Q 9.11** Do goals stay within the commit budget they set themselves?
- **Q 9.12** How long is a PR open, and does that grow with the number of change sets it carries?
- **Q 9.13** Where does a PR's open time go: agent working, CI, waiting for the owner, usage limits, or no session open?
- **Q 9.14** How many sessions does it take to carry a PR to merge, and how long are the pauses between them?
- **Q 9.15** When does work land, by day of the week and hour of the day?
- **Q 9.16** Does a change set's size predict how long its PR stays open?

## Chapter 10 · Agent mistakes and rework

- **Q 10.01** Where does the factory record an agent's mistakes, and since when?
- **Q 10.02** Which gates leave a verdict a script can read, and which leave nothing?
- **Q 10.03** How much of each PR's work is fixing that same PR before it merges?
- **Q 10.04** How often does a merged PR need a fix-forward, how soon, and is that falling?
- **Q 10.05** How often did something go wrong badly enough to revert or reopen?
- **Q 10.06** How long does a defect live between the PR that introduced it and the PR that fixed it?
- **Q 10.07** Whose defect is it: this factory's earlier work, the template, or something older?
- **Q 10.08** What kinds of mistakes do agents make, and which keep recurring?
- **Q 10.09** Who catches the mistakes: the agent itself, review agents, CI, the judge, or the owner?
- **Q 10.10** Where do the fixes land: product code, tests, CI, config or docs, and how many are security fixes?
- **Q 10.11** How often is "done" not actually done, and what closes the gap?
- **Q 10.12** How have the reviewer and the judge changed, and how often does each send work back?
- **Q 10.13** Does each review persona earn its place?
- **Q 10.14** How often did a check pass without really checking, and who noticed?
- **Q 10.15** What happens to the problems an agent finds but doesn't fix: filed, done, or left to sit?
- **Q 10.16** When a work item is marked ready, how often does it need replanning afterwards?
- **Q 10.17** Are agents erring less, or just being corrected less?

## Chapter 11 · Security

- **Q 11.01** When did each repo get secret, dependency and container scanning, and does each run in CI or only as a local hook?
- **Q 11.02** How far do supply-chain pins reach (action SHA pins, image digest pins, Dependabot coverage of every manifest), and how did the coverage grow?
- **Q 11.03** How much of the fleet's work is security work, and how has that share moved as the factory grew?
- **Q 11.04** Where are security problems found: a scanner, Dependabot, a review bot, an audit, the owner, or production?
- **Q 11.05** How often does code review flag a security problem in a PR, how severe is it, and is the rate falling?
- **Q 11.06** When an agent's own change introduced a security defect, how long did it sit on main, and did it reach production?
- **Q 11.07** How long does a security finding take from discovery to merged fix, and how many are still open?
- **Q 11.08** When a dependency gets a security fix, how long does each repo take to apply it, how many never do, and how often is the same advisory fixed separately in several repos?
- **Q 11.09** When a hardening fix lands in one repo, how long until the siblings with the same defect are fixed, and did each fix it the same way?
- **Q 11.10** How much upkeep do dependency bumps cost each week (PRs opened, merged, thrown away, CI minutes), and does grouping make it smaller?
- **Q 11.11** How often has a scanner or its suppressions been wrong: an ignore that outlived its CVE, a scan aimed at the wrong target, a gate that could not fail?
- **Q 11.12** Can the auto-approve judge be tricked into approving, and how much of that has been tested rather than assumed?
- **Q 11.13** Where do the plugin's own security fixes come from (its own review, a consuming repo, or the owner), and did each remove the risky mechanism or only narrow it?
- **Q 11.14** How often is a work item marked done while one of its own security acceptance criteria is not met?
- **Q 11.15** Does a repo's documentation claim a security control the repo does not have, and where did each false claim come from?
- **Q 11.16** What infrastructure security risks has the fleet recorded (credential blast radius, secrets in boot config, network exposure, revocation latency), and which have been checked live?
- **Q 11.17** Has a secret ever been committed to a repo, and how long did it stay before it was found and rotated?

## Chapter 12 · Fleet scope and apps

- **Q 12.01** How many repos did the fleet hold each month, of which kinds, and when did each one join or leave?
- **Q 12.02** Since when has the fleet had a map, and how closely does it match the repos actually checked out?
- **Q 12.03** Did every app with a dev stack claim its own port, and how long did new clones sit on the template's port?
- **Q 12.04** Does the fleet say what each kind of repo must contain, and how much of it does each repo actually have?
- **Q 12.05** What shape is the template, and how did that shape change as it matured?
- **Q 12.06** Which template version did each clone start from, and how much of the template does each clone still share today?
- **Q 12.07** How many repos share the template's stack, and is the fleet converging on it or drifting apart?
- **Q 12.08** Which apps depend on the shared services (identity, the design-system registry, the infrastructure repos), and do their design records say so?
- **Q 12.09** Is the design system shipping components apps can use, or is its own scaffolding growing faster?
- **Q 12.10** How much work has each app received over its life, in change sets, and does it rise, plateau or fall with age?
- **Q 12.11** How much of each app's work is features, and how much is structural work (fixes, chores, security, dependencies, docs), and did the mix shift when larger Opus models took over?
- **Q 12.12** For each app, how many planned features have shipped and how many are still open, week by week?
- **Q 12.13** How does each app's code grow, split into code written for it, generated code and vendored code?
- **Q 12.14** How long does a new app take to go from creation to its first shipped feature and its first live deploy?
- **Q 12.15** When an app's API route and its UI proxy allowlist must change together, do both halves land in the same PR?

## Chapter 13 · Cross-repo context and messaging

- **Q 13.01** What channels have repos used to pass requests and context to each other, and when did each start carrying traffic?
- **Q 13.02** Which way do messages flow: from shared repos down to their consumers, or up from consumers to the shared repos?
- **Q 13.03** Of the messages sent, how many reached the recipient's inbox, and how many were answered, declined or are still waiting?
- **Q 13.04** Once a message is delivered, how many days until the receiving repo answers or acts on it, and does an awaited message get answered faster?
- **Q 13.05** When an agent finds that another repo needs to change, does it send a message, file it locally, fix the other repo itself, or drop it, and how soon?
- **Q 13.06** When a repo acts on a message, how far does the work it ships differ from what the message asked for?
- **Q 13.07** How much does an agent working in one repo know about its siblings, and where does it get that from?
- **Q 13.08** How often does a session in one repo change another repo directly, and did that stop when the mailbox made it against the rules?
- **Q 13.09** When the same change lands in several repos, how often was it made once upstream and carried out, and how often did each repo make it on its own?
- **Q 13.10** Once a change exists upstream, how many days until each consumer has it, and how many consumers still do not?
- **Q 13.11** Do the rules, hooks and workflows vendored from wayfare stay current in each repo, or go stale until the next re-vendor?
- **Q 13.12** How does a change actually get carried across the fleet: a fleet-root fan-out, a message, or the owner opening each repo in turn?
- **Q 13.13** When a sweep lands in many repos, is each PR reviewed, and how many problems surface after merge instead?
- **Q 13.14** How do repos consume shared pieces: by a moving reference, a vendored copy, or a pinned version, and how has that mix changed?
- **Q 13.15** When an upstream change broke its consumers, how many repos broke, and how long until each was fixed?
- **Q 13.16** When an upstream change affects its consumers, does the change say which repos it affects?
- **Q 13.17** Where a decision should hold in every repo, do the design records agree, and how long does a disagreement last?
- **Q 13.18** When scope or a convention moves from one repo to another, do both repos' records say who owns it now?

## Chapter 14 · Compliance and drift

- **Q 14.01** How has the control register grown since it was created, and what share of its checks can a machine run?
- **Q 14.02** What prompted each control: a bug seen in a fleet repo, an outside incident or advisory, or a design choice made before anything broke?
- **Q 14.03** Who changes the rules, and does a rule change pass the same review gate as code?
- **Q 14.04** How often is the fleet actually checked against the register, and how stale is the picture between checks?
- **Q 14.05** At each audit, what share of check × repo results passed, and which repos pulled the rate down?
- **Q 14.06** When a new check is written, how many repos already break it, and how long had they been breaking it?
- **Q 14.07** Once a check catches a repo, how long until that repo passes, and what share never does?
- **Q 14.08** Which failures are still open, and are they worked in severity order when no control has a deadline?
- **Q 14.09** Does a new clone start as compliant as the template, and does it stay there?
- **Q 14.10** Do copies of the register and of other vendored rules drift from their source, and what catches them?
- **Q 14.11** How much of the fleet's work and spend goes to compliance and hardening rather than product?
- **Q 14.12** How often does a change name the control or check it serves?
- **Q 14.13** Do commits to the gates only tighten them, and what precedes a loosening?
- **Q 14.14** When a gate fails, does the agent fix the code or silence the gate?
- **Q 14.15** Do the instruction files that state the factory's rules pass those rules themselves?

## Chapter 15 · Deployment and infrastructure

- **Q 15.01** How did the platform a merged change lands on evolve over the year?
- **Q 15.02** How long does it take a new app to go from its first commit to provisioned infrastructure?
- **Q 15.03** Which provisioned apps actually deploy on merge, and since when?
- **Q 15.04** How long does a merged change take to reach production, and has that shortened?
- **Q 15.05** How often does a deploy fail, and what brought it back?
- **Q 15.06** Is production up, and do outages line up with deploys?
- **Q 15.07** How often does a PR's CI go red, and has that fallen as local checks moved earlier?
- **Q 15.08** When a PR's CI goes red, what turns it green, and how long does it take?
- **Q 15.09** Which checks fail and then pass on the same commit, and is that getting rarer?
- **Q 15.10** Which checks have never failed in the observed history, and could they?
- **Q 15.11** When a shared workflow changes, how many repos break, and for how long?
- **Q 15.12** How fast does a pin bump (an action, a provider, a base image) reach every repo, and how many lag?
- **Q 15.13** Is the infrastructure built by the factory the same way the apps are?

## Chapter 16 · Spend and cost

- **Q 16.01** How much does the factory spend a week, and in which repos?
- **Q 16.02** How much of the spend can be traced to the change set it produced?
- **Q 16.03** What does one change set cost, and has that fallen as the factory matured?
- **Q 16.04** How does cost roll up from change set to PR, work item and goal?
- **Q 16.05** What does the factory actually pay compared with the cost the harness reports?
- **Q 16.06** Which models carry the spend, and what does a change set cost on each?
- **Q 16.07** How much of the spend goes to subagents, and to which kind?
- **Q 16.08** What does review cost per change set, and does it grow with the size or risk of the change?
- **Q 16.09** What share of spend goes to features, fixes, security and upkeep, and how has the mix moved?
- **Q 16.10** How many CI minutes does the fleet use a week, and on which workflows?
- **Q 16.11** How many CI minutes go to runs that could not change an outcome?
- **Q 16.12** How much spend and CI goes to dependency updates rather than the owner's own work?
- **Q 16.13** Did the fleet's CI changes lower CI minutes per change set?
- **Q 16.14** What does a change cost when it is made in several repos instead of once upstream?

## Chapter 17 · Factory floor efficiency

- **Q 17.01** Can each shipped change set be traced to its cost, its wall time and any later fix?
- **Q 17.02** Where does the factory's session clock go: working, waiting on the owner, stopped by a limit, or idle?
- **Q 17.03** How often did usage limits stop the factory, how long did each stop last, and what changed them?
- **Q 17.04** When the factory waits on the owner, how long does it wait, in a session and at a PR?
- **Q 17.05** How many sessions run at once, and how close does the factory come to the owner's ceiling of about six?
- **Q 17.06** How much work does the factory carry in progress: open PRs and unfinished work items?
- **Q 17.07** How long does work take from start to merge, at the PR and at the work item, and do the two agree?
- **Q 17.08** How much of the factory's work happens while the owner is away from the keyboard?
- **Q 17.09** What share of spend and opened work never ships: PRs closed unmerged, items dropped, merges reverted?
- **Q 17.10** What share of merged change sets ship right the first time, with no follow-up fix within a week?
- **Q 17.11** How much session effort is thrown away: tool calls that error or are rejected, and limit-cut sessions?
- **Q 17.12** Does the factory's output rise with the hours it works, or does it stay flat as more sessions run?
- **Q 17.13** Summed into one OEE-style score per week (availability × performance × quality), how efficient is the factory, and which factor holds it down?

## Chapter 18 · The factory manager's thinking

- **Q 18.01** Where does the factory write down why a rule, gate or skill exists, and how much of that record carries a reason?
- **Q 18.02** How did the owner split attention between building the products and building the factory?
- **Q 18.03** Did the owner's corrections move from direction and taste to catching the agent's errors?
- **Q 18.04** When the owner corrects an agent, how often does it become a memory, and how long after?
- **Q 18.05** What prompted each change to the auto-approve gate?
- **Q 18.06** Were the register's controls written after an incident, as the owner says?
- **Q 18.07** When and why did the fleet get a shared control register?
- **Q 18.08** Which rules did the owner have to restate most?
- **Q 18.09** What triggered each restructuring of the plugin's names and layout, and what broke after each?
- **Q 18.10** What did the owner change because of spend and usage limits?
- **Q 18.11** How often did the owner act as the go-between for concurrent agent sessions, and did the mailbox take that over?
- **Q 18.12** When did the owner trade care for speed, and what did it cost in follow-up fixes?
- **Q 18.13** Which incidents were followed by the biggest bursts of factory change?
- **Q 18.14** Did practices flow up from the products into the template and plugin, or down from them?

## Chapter 19: Toward an architecture (questions)

- **Q 19.01** What are the factory's components, when did each first ship, and which are still in use today?
- **Q 19.02** In what order did each repo take the components up, and do repos skip or reorder steps?
- **Q 19.03** How long after a component shipped did each repo start using it?
- **Q 19.04** Which components were built and then removed or replaced, and how long did each live?
- **Q 19.05** What share of the fleet's change sets passed through each component, week by week?
- **Q 19.06** How did an app's weekly output change in the weeks after it took each component up?
- **Q 19.07** Did follow-up fixes after a merge become more or less common after an app took each component up?
- **Q 19.08** Did the owner's hands-on share of the work fall after an app took each component up?
- **Q 19.09** Does work that goes through more of the architecture cost more or less per change set?
- **Q 19.10** How do the components depend on each other, and has that web grown more tangled or simpler?
- **Q 19.11** Did any repo use a later component without an earlier one, and how did those weeks go?
- **Q 19.12** Which components reach a repo through the template at creation, and which arrive later through the plugin?
- **Q 19.13** How much of the change around each milestone coincides with a new model or Claude Code release instead?
- **Q 19.14** What order of adoption does the fleet's evidence support for a new factory?

## Chapter 20: The field, and what generalizes

- **Q 20.01** Could another factory ask this study's questions of itself, or are they written in this fleet's names?
- **Q 20.02** How much of this study could another factory measure from stock git and GitHub history, how much needs agent transcripts, and how much needs wayfare's own records?
- **Q 20.03** Can the fleet's separate logs merge into one timeline that replays what happened, and at what time resolution?
- **Q 20.04** Is each number this chapter compares with the field defined in a unit another factory could reproduce, and do the published figures use the same one?
- **Q 20.05** What share of merged changes reached main with no human action between the request and the merge, and how has that share moved as the factory evolved?
- **Q 20.06** Did human review work per merged change grow as the fleet's volume grew, the way large deployments report?
- **Q 20.07** How did measured throughput change as each repo moved through the stages, and does it match what the owner believes the factory sped up?
- **Q 20.08** At which stages does a human read the agent's intermediate output (idea, plan, PR, merge), and how has that placement moved over time?
- **Q 20.09** Did each new repo get onto the factory faster than the one before it?
- **Q 20.10** What is the smallest part of the control register another factory could reuse, and do its honesty signals (exemption share, gaps closed per audit) hold up over time?
- **Q 20.11** Which verification practices did the factory adopt after a specific failure, and did the kind of failure they target stop recurring afterwards?
- **Q 20.12** How close did one operator's coordination conventions (a hand-kept port map, drift checks that need every checkout local, one person's history) come to their limit as repos and parallel work grew?

## Chapter 21 · Conclusion and next steps

- **Q 21.01** What did the factory ship in total, and in which repos and weeks?
- **Q 21.02** At each stage, how did throughput, rework, spend and owner time per change set compare?
- **Q 21.03** Did quality hold as throughput rose?
- **Q 21.04** How many change sets does an hour of the owner's attention buy, and is that rising?
- **Q 21.05** How long does the factory run without the owner, and is that stretch growing?
- **Q 21.06** Does adding repos add output, or split a fixed amount of owner attention?
- **Q 21.07** Which constraint binds the factory now: owner attention, rate limits, spend or CI?
- **Q 21.08** Did the gains coincide with wayfare's milestones, or with new models and Claude Code releases?
- **Q 21.09** Is the one-shot gap closing, and in which repos is it still open?
- **Q 21.10** Which evidence covers which weeks, and which practices predate their own data?
- **Q 21.11** What share of agent sessions and spend leads to no merged change?
- **Q 21.12** Which of the study's questions could not be answered, and why?
- **Q 21.13** Which of the owner's hypotheses held, and which findings were surprises?
- **Q 21.14** Is the backlog shrinking or growing, and how old is the open work?
- **Q 21.15** Where does new work come from now: the owner, the audits, messages, or one-shot tasks?
- **Q 21.16** Which recurring problems has the factory not yet fixed at the source?
- **Q 21.17** Which next steps does the evidence most support, ranked by what each would save?
