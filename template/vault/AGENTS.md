# Vault: {{NAME}} (schema, read before writing)

{{DESCRIPTION}}

This vault follows the LLM-wiki pattern: agents write and maintain the wiki, humans
supply sources and approve what counts as truth. Workspace-wide rules live in the
workspace `AGENTS.md`; this file only adds what is specific to this vault.

## Scope

- **Here**: everything that belongs to {{NAME}}.
- **Never here**: material that belongs to another vault. Link to it by title, do not copy it.

## Structure

| Path | Role | Who writes |
|---|---|---|
| `AGENTS.md` | this schema | pull request only |
| `index.md` | catalogue of every wiki page (link + one line) | the curator agent, on every ingest |
| `log.md` | append-only journal, `## [YYYY-MM-DD] <ingest\|query\|lint\|decision> \| <title>` | any agent that ingests, lints or records a decision |
| `raw/` | immutable sources: documents received, transcripts, exports | append only, never rewrite |
| `wiki/canon/` | truth: `CANON-*.md`, one volatile fact per page | pull request only |
| `wiki/projects/` | work in progress | agents |
| `wiki/_archive/` | superseded pages | agents |

## Rules

1. A volatile fact (price, date, contact, scope, KPI) lives in exactly one `wiki/canon/CANON-*.md`.
   Everywhere else, link to it; never copy the value.
2. Read the canon before stating a volatile fact.
3. Changing a canon = pull request with the reason and the source. A value in an open PR is not true yet.
4. `raw/` is never rewritten. Fix the wiki page that cites the source instead.
5. Outdated page: `status: superseded` plus a one-line banner, then move it to `wiki/_archive/`.
6. Canon frontmatter: `status`, `canonical`, `last_verified`, `review_cadence`.
7. No secrets, ever.
