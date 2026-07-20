---
description: UI constraints for the AI Hero design system — registry components and semantic tokens only.
paths:
  - "**/*.tsx"
  - "**/*.jsx"
  - "**/*.css"
---

# UI: the AI Hero design system

UI comes from AI Hero's private shadcn registry (`@aihero`) — not from scratch,
not from stock shadcn. **Before writing any component, search the registry.**
There are ~160 items (button, card, field, table, chart-\*, app-shell, top-bar,
landing-page, …):

```bash
npx shadcn@latest search @aihero -q "WHAT_YOU_NEED"
npx shadcn@latest view @aihero/ITEM      # inspect the API first
npx shadcn@latest add @aihero/ITEM
```

Hand-rolling a component that already exists in the registry is the primary
defect this rule prevents.

## Vendored, not authored

Installed components land in `src/components/ui/` (primitives) and
`src/components/blocks/` (sections). **Never edit them in place.** A local edit is
silently reverted by the next `shadcn add --overwrite`. To change one: compose
around it, pass `className` (every item merges via `cn()`), or change it upstream
in the design system and re-add.

## Tokens only

Semantic classes only — `bg-background`, `text-muted-foreground`, `border-input`,
`bg-destructive`. Never raw palette (`bg-zinc-100`, `text-gray-500`), never hex or
`oklch()` literals in components; those belong in the `@theme` token layer.

- Text on a colored surface uses the paired foreground token (`bg-primary` →
  `text-primary-foreground`), never an eyeballed shade.
- Dark mode comes free via tokens and the `.dark` class — never
  `prefers-color-scheme`. **A `dark:` color override means you used the wrong
  token.**

## Spacing, shape, type

- **Parents own layout.** Use `gap-*` / `space-*` in the container; components
  never carry margins (`m-*`, `mt-*`, `ms-*`) on their root element.
- Spacing scale only — no `p-[13px]`, `gap-[7px]`. If the scale lacks a step, the
  design is wrong, not the scale.
- Radii from the token scale (`rounded-sm|md|lg|full`); no `rounded-[10px]`.
- **No shadows** — elevation is borders and hairlines. `--shadow-*: initial` makes
  any `shadow-*` class a lint error, by design.
- z-index from the named scale (`z-dropdown` < `z-sticky` < `z-overlay` <
  `z-modal` < `z-toast`); never `z-[9999]`.
- Type from the scale (`text-sm`, `font-medium`, tracking tokens); no arbitrary
  font sizes.
- Variants via `cva` with typed props — no ternary/string-concat className soup.
  Merge with `cn()`. Never hand-sort classes; `prettier-plugin-tailwindcss` owns
  the order.

## Icons and accessibility

- Lucide only, sized `size-4` / `size-5`, `aria-hidden` unless the icon is the
  only label.
- Every interactive element has a visible `focus-visible:` ring. Removing an
  outline without a replacement is a defect.
- Disabled states use `disabled:` variants + `aria-disabled`, not opacity hacks
  on wrapper divs.
- Respect `prefers-reduced-motion` for any animation.

## Component layers

Vendored registry code stays flat; this app's own components are atomic:

```
src/components/
├── ui/          # vendored registry primitives  — never edit
├── blocks/      # vendored registry sections    — never edit
├── atoms/       # app-specific primitives the registry lacks (rare)
├── molecules/   # compositions of ui/ + atoms/
├── organisms/   # domain-aware sections
└── templates/   # layout shells with slot props — structure only, zero copy
```

Imports flow **downward only**: templates → organisms → molecules → atoms →
(`ui/`, `blocks/`). `ui/` and `blocks/` are the floor — any layer may import them.
Place each component at the lowest layer that fits; promote only when it gains
domain knowledge or composition, never preemptively.

`atoms`/`molecules` are stateless and generic — no fetching, no auth, no domain
types. `organisms` may hold domain types but still receive data via props.
`templates` never hardcode copy.

## Auth

`REGISTRY_TOKEN` (a Personal Access Token from `auth.aihero.studio/profile`) is
the only registry variable this project needs. **Never commit it.**

It must live in the `.env` **next to `components.json`** — not the repo-root
`.env`, even where that is the house convention for every other secret. The CLI
resolves env relative to the config directory, not the working directory; a
root-level token fails with `Set the required environment variables to your .env
or .env.local file`, which misleadingly reads as a missing variable. Exporting
`REGISTRY_TOKEN` in the shell works too and avoids a second copy of the secret.

In `components.json` write the plain `${REGISTRY_TOKEN}` form only — the CLI regex
is `/\$\{(\w+)\}/g`, so `${VAR:-default}` ships as a literal string and surfaces
as a confusing 401.

Full procedure: `hero-skills:upgrade-ui`.
