---
name: vault-wiki
description: Maintain a workspace of agent-maintained vaults (LLM-wiki pattern) — route inbox captures to the right vault, ingest sources into wiki pages, answer from the wiki, run the nightly lint, and propose every canon change as a pull request approved by a human. Use for any curator session, any ingestion, any lint, and whenever an agent wants to change an AGENTS.md, a CANON-* page, a SKILL.md or vaults.toml.
---

# Vaults are wikis kept by agents; canons are approved by humans

## Mental model

The workspace holds several vaults, each with its own repository and access list (registry:
`vaults.toml`, map: the workspace `AGENTS.md`). The owner sees everything; a partner or a client sees
only their vault. So **picking the vault is a confidentiality decision**: client material in the
company vault leaks to partners; personal material outside the owner vault leaks to everyone.

Each vault has three layers:

| Layer | Where | Rule |
|---|---|---|
| Raw | `raw/` | immutable sources: add, never rewrite |
| Wiki | `wiki/` | pages written by agents; `index.md` catalogues them, `log.md` records every operation |
| Schema / canon | `AGENTS.md`, `CLAUDE.md`, `wiki/canon/`, `skills/*/SKILL.md`, `vaults.toml` | pull request + human approval |

## Changing a canon: propose, don't edit

Put the change on a branch, open a pull request whose body gives the reason, the source (a `raw/`
path or a URL) and any contradiction found. One PR, one topic. Never present a value from an open PR
as true. Only a human merges. Branch protection plus a `CODEOWNERS` entry on canon paths makes this
enforceable, not just polite.

## Ingest (inbox → right vault)

For each item in the owner inbox:

1. Decide the vault: named client → that client's vault; company matter → company; personal → owner;
   doubt → leave it in the inbox and say so. An item that mixes scopes is split, each part to its vault.
2. Move the source as-is into that vault's `raw/` (content untouched).
3. Write or update the `wiki/` pages it touches: summary plus a link to the source.
4. Contradiction with a canon → PR on the canon, never a direct edit.
5. One line in `index.md` per new page; one entry `## [YYYY-MM-DD] ingest | <title>` in `log.md`
   (`vaultctl log <vault> ingest "<title>" --body "..."`).

In unattended runs: items older than 7 days only, at most 5 per run.

## Query

Read `index.md`, then the pages. Quote canons for volatile facts. An answer that will be asked again
becomes a wiki page (and a line in `index.md`).

## Lint (nightly)

1. `vaultctl check <workspace> --since <yesterday's commit>`: structure, canon frontmatter and review
   dates, broken links, pages missing from `index.md`, malformed `log.md`, secrets, private terms
   leaking across vaults, `raw/` files modified or deleted.
2. Judgement pass the script cannot do: wiki pages contradicting a canon, volatile values copied
   outside the canon, inbox items older than 7 days, PRs open for more than 3 days.
3. A deleted raw file may be an intact move: compare contents before calling it a loss.
4. Closed-without-merge PRs and review comments become `feedback-*` notes in the agents' memory:
   human corrections are how agents improve.

Output: a short message to the owner with counts per vault and PR links. Nothing to report = one line.

## Never

Write a secret · rewrite a raw file · put content in a vault that is not its own · edit a canon
without a PR · merge a PR.
