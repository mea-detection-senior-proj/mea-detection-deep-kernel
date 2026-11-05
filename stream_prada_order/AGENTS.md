# Persistent isolation rules

- Work only on `experiment/stream-prada-order` in the isolated worktree.
- Before each commit check `git branch --show-current`; abort on any other branch.
- Never integrate, merge, rebase, cherry-pick or transfer experiment commits into
  `main` or another integration branch. Never create an integration PR.
- Do not push without a new explicit authorization. Stop after the local commit.
- Do not edit teammate implementations in PRADA, pilot, or Deep Kernel MMD.
- Preserve blocked runs and their provenance. Resource-gate failure requires
  explicit approval before running beyond the original 1,200-second gate.
- No synthetic research sentences as experimental queries. Synthetic numeric
  fixtures are allowed only for unit tests.
- Do not commit raw queries, model weights, embeddings, caches, secrets, or large
  artifacts. Report null for unmeasured quantities and keep uncertainty conditional
  on the fixed query sets and simulated schedules.
