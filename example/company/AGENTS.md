# Vault: Company (schema, read before writing)

The company itself: what it sells, how it works, its agents and their skills. Workspace rules in
`../AGENTS.md` apply; this file adds what is specific to this vault.

## Scope

- **Here**: offers, positioning, legal entity, methods, internal tooling, prospects before a contract.
- **Not here**: a client's work material (it has its own vault), personal material (owner vault).
  A company page may name a client; it never contains that client's documents, contacts or figures.

## Structure

| Path | Role | Who writes |
|---|---|---|
| `AGENTS.md` | this schema | pull request only |
| `index.md` | catalogue of every wiki page | the curator agent, on every ingest |
| `log.md` | append-only journal | any agent that ingests, lints or decides |
| `raw/` | immutable sources: call notes, research, exports | append only |
| `wiki/canon/` | truth: `CANON-*.md` (entity, offers, stack…) | pull request only |
| `wiki/projects/` | initiatives in progress | agents |
| `wiki/resources/` | reusable methods, checklists, templates | agents |
| `wiki/_archive/` | superseded pages | agents |

## Default permission

Pages here are `company_private` unless their frontmatter says otherwise.
