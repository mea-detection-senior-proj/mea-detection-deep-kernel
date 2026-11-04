# Domain docs

This repo uses a single-context layout.

## Before exploring

- Read `GLOSSARY.md` at the repo root.
- Read decisions in `docs/adr/` relevant to the area being explored.

If these files or directories do not exist, proceed silently.
The domain-modeling skill creates them as terms and decisions are resolved.

## Layout

- `GLOSSARY.md`: shared domain terms.
- `docs/adr/NNNN-<decision-slug>.md`: numbered architecture decisions.

## Vocabulary

Use glossary terms in issue titles, proposals, hypotheses, and test names.
If a needed concept is missing, reconsider the wording or note the gap
for domain-modeling.

## Decision conflicts

If a proposal contradicts an existing ADR, identify that ADR and explain
why the decision should be reconsidered.
