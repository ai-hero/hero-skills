---
name: hero-init clarification style
description: hero-init should ask numbered questions or use plan mode for clarifications, never ask about gitignore, always commit HERO.md
type: feedback
---

When hero-init needs clarification, always ask questions in a numbered list format, or switch to plan mode to ask them. Never ask freeform unstructured questions.

**Why:** User wants a clean, structured interaction when gathering project context. Unstructured questions are harder to parse and respond to.

**How to apply:** In the hero-init skill prompt/flow, format all clarifying questions as numbered items (1. 2. 3.) or enter plan mode before asking.

---

HERO.md must always be committed after creation or update. Do not ask the user whether to commit — just do it.

**Why:** HERO.md is a core project artifact that should always be tracked in version control.

**How to apply:** After writing/updating HERO.md, automatically stage and commit it. Never ask about adding it to .gitignore or whether to commit it.
