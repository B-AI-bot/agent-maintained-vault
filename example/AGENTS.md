# Workspace router (read before writing anything)

Single source of instructions for every agent working here (Claude Code, Codex CLI, Hermes Agent
or any other). `CLAUDE.md` is only a pointer to this file.

`vaultctl` below means `python3 path/to/tools/vaultctl.py` from the template repository.

This folder holds **several independent vaults**. Each one is an LLM-maintained wiki with its own
git repository and its own access list. The owner sees everything; a partner or a client only sees
the vault opened to them. **Choosing the right vault is a confidentiality decision, not filing.**

## Which vault?

The registry is [`vaults.toml`](vaults.toml).

| Vault | Folder | Holds |
|---|---|---|
| Company | `company/` | offers, positioning, methods, agents, skills. May *name* a client, never hold its work material |
| Owner | `owner/` | inbox, journal, agents' shared memory, personal admin. Owner only |
| One per client | `clients/<slug>/` | everything produced for or received from that client |

New client: `vaultctl new clients/<slug> --name "<Client>"`, then add it to
`vaults.toml` by pull request and create its repository.

## Same structure in every vault

`AGENTS.md` (schema, PR) · `index.md` (catalogue, kept by the curator) · `log.md` (append-only,
`## [YYYY-MM-DD] <ingest|query|lint|decision> | <title>`) · `raw/` (immutable sources) ·
`wiki/` (pages written by agents) · `wiki/canon/` (truth, `CANON-*.md`, PR).

## Rules

1. **One fact, one vault, one page.** A volatile fact (price, status, contract, contact, KPI) lives in one
   `wiki/canon/CANON-*.md` of the vault it belongs to. Elsewhere, link; never copy the value.
   Client material never goes into `company/` or another client's vault; personal material never leaves `owner/`.
2. **Read the canon before stating a volatile fact.** Each vault's `wiki/canon/` folder is its register.
3. **Captures land in `owner/raw/inbox/`.** The curator routes each one to the right vault.
4. **The journal is history** (`owner/raw/journal/`). Never quote it as current truth.
5. **Outdated content:** `status: superseded` plus a banner, then `wiki/_archive/` of the same vault.
6. **Canon frontmatter:** `status`, `canonical`, `last_verified`, `review_cadence`.
7. **Canon changes by pull request, never directly.** Canon = `AGENTS.md`, `CLAUDE.md`, `vaults.toml`,
   `wiki/canon/**`, `skills/*/SKILL.md`. The PR says why and cites the source. A value in an open PR is
   not true. Only a human merges.
8. **`raw/` is never rewritten.** Add files; correct the wiki page that cites them instead.
9. **No secrets in any vault.** Credentials live in a secret manager; pages may name the secret, never hold it.

## Operations

- **Ingest**: read the source, store it in `raw/` of the right vault, write or update the wiki pages it
  touches (summary + link to the source), open a PR if it contradicts a canon, add new pages to
  `index.md`, append one entry to `log.md`.
- **Query**: read `index.md`, then the pages. An answer worth reusing becomes a wiki page.
- **Lint** (nightly): `vaultctl check .` plus a judgement pass: contradictions between
  wiki and canon, values copied outside the canon, inbox items older than 7 days, open PRs older than
  3 days. Report in a few lines; propose fixes, do not rewrite in bulk.

Full operating manual for agents: `skills/vault-wiki/SKILL.md`.

## Knowledge permissions (optional frontmatter)

Pages that may travel (into a search index, a client deliverable, a public post) carry
`knowledge_permission`, one of: `personal_private`, `company_private`, `customer_private`,
`customer_visible`, `deidentified_reusable`, `public`. The only bridge from client data to reusable
company knowledge is `customer_private` → human-approved de-identification → `deidentified_reusable`.
See [company/wiki/resources/knowledge-permissions.md](company/wiki/resources/knowledge-permissions.md).

## Retrieval index

If a semantic index (vector store, knowledge graph, `gbrain`…) reads the vaults, it indexes committed
`wiki/` pages only: never `raw/inbox/`, never uncommitted files, never `personal_private` outside `owner/`.
