# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`GLOSSARY.md`** at the repo root, or
- **`GLOSSARY-MAP.md`** at the repo root if it exists: it points at one `GLOSSARY.md` per context. Read each one relevant to the topic.
- **`docs/adr/`**: read ADRs that touch the area you're about to work in. In multi-context repos, also check `projects/<project>/docs/adr/` for project-scoped decisions.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill (reached via `/grill-with-docs` and `/improve-codebase-architecture`) creates them lazily when terms or decisions actually get resolved.

## File structure

Multi-context monorepo (this repo): each project in `projects/` is its own context, with its own glossary and ADRs. Repo-wide decisions live at the root.

```
/
├── GLOSSARY-MAP.md              ← lists each project's glossary
├── docs/adr/                    ← repo-wide decisions (e.g. monorepo conventions)
├── learning/                    ← no glossary or ADRs (low-ceremony exercises)
└── projects/
    └── 01-hdb-resale/
        ├── GLOSSARY.md
        └── docs/adr/            ← project-scoped decisions
```

A new project gets its own `GLOSSARY.md` and `docs/adr/` (created lazily) and a line in `GLOSSARY-MAP.md`. ADR numbering restarts at 0001 in each `docs/adr/` folder; refer to them as "repo ADR-NNNN" or "project ADR-NNNN" when ambiguous.

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `GLOSSARY.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal: either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders), but worth reopening because…_
