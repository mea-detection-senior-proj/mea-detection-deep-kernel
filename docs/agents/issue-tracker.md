# Issue tracker: Local Markdown

Issues and specs live as Markdown files under `.scratch/`.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`.
- Specs: `.scratch/<feature-slug>/spec.md`.
- Implementation tickets: `.scratch/<feature-slug>/issues/<NN>-<slug>.md`,
  numbered from `01`, with one file per ticket.
- Record triage state in a `Status:` line near the top of each ticket,
  using the roles in `triage-labels.md`.
- Append comments and conversation history under `## Comments`.
- Reference tickets by their full repo-relative path; numbers are scoped
  to a feature directory.

## Publishing and fetching

When a skill says “publish to the issue tracker,” create the spec or
individual ticket files at the paths above, creating directories as needed.

When a skill says “fetch the relevant ticket,” read the referenced file.
If only a number is supplied, resolve it within the relevant feature.

## Wayfinding operations

Used by `/wayfinder`.

- Map: `.scratch/<effort>/map.md`, containing Notes, Decisions-so-far,
  and Fog.
- Child tickets: `.scratch/<effort>/issues/<NN>-<slug>.md`.
- Type: a `Type:` line containing `research`, `prototype`, `grilling`,
  or `task`.
- Lifecycle: wayfinding tickets use `Status: open`, `Status: claimed`,
  or `Status: resolved`.
- Blocking: a `Blocked by: NN, NN` line refers to tickets in the same
  effort. A ticket is unblocked when all listed blockers are resolved.
- Frontier: select the first open, unblocked ticket by number.
- Claim: save `Status: claimed` before starting work.
- Resolve: append the answer under `## Answer`, set `Status: resolved`,
  then append a brief finding and ticket link to Decisions-so-far
  in the map.
