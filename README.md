# agent-maintained-vault

A template for a knowledge base that AI agents write and humans govern.

It follows the "LLM wiki" pattern described by Andrej Karpathy: instead of re-reading raw documents
on every question, agents compile sources into a wiki of plain Markdown pages, keep an index and a
log, and lint the whole thing regularly. This template adds the parts you need once several agents,
several clients and real money are involved: one vault per confidentiality scope, a small set of
"canon" pages that only change through a human-approved pull request, append-only sources, and a
linter that catches what drifts.

Works with Obsidian (or any Markdown editor) and any agent you can point at an `AGENTS.md` file
(Claude Code through the `CLAUDE.md` pointer, Codex CLI, Hermes Agent, and others).

## What's inside

```
example/                      a complete fictional workspace (lint-clean)
  AGENTS.md                   workspace router: which vault, the rules, the operations
  CLAUDE.md                   pointer to AGENTS.md
  vaults.toml                 registry of vaults, with private terms for leak detection
  company/                    the company vault
  owner/                      owner-only vault: inbox, journal, agents' shared memory
  clients/acme-bakery/        one vault per client
template/vault/               blank vault, used by `vaultctl new`
skills/vault-wiki/SKILL.md    operating manual for agents (Agent Skills format)
tools/vaultctl.py             linter and scaffolder, Python standard library only
tests/                        unit tests for vaultctl
```

Every vault has the same shape:

| Path | Role | Who writes |
|---|---|---|
| `AGENTS.md` | schema of the vault | pull request only |
| `index.md` | catalogue of every wiki page, one line each | the curator agent |
| `log.md` | append-only journal, `## [YYYY-MM-DD] <ingest\|query\|lint\|decision> \| <title>` | every agent |
| `raw/` | immutable sources: transcripts, documents received, exports | append only |
| `wiki/` | pages compiled by agents | agents |
| `wiki/canon/` | the truth: `CANON-*.md`, one volatile fact in one place | pull request only |
| `wiki/_archive/` | superseded pages | agents |

## The rules that make it hold

1. **One fact, one vault, one page.** A price, a date, a contact or a scope lives in a single
   `wiki/canon/CANON-*.md`. Every other page links to it. When it changes, it changes once.
2. **Canons change by pull request.** The agent writes the change on a branch with the reason and the
   source; a human merges. A value in an open PR is not true yet.
3. **Sources are never rewritten.** `raw/` is append-only, so every wiki claim can be traced back.
4. **The vault is a confidentiality boundary.** One repository per vault, one access list per
   repository. A partner sees the company vault, a client sees their own, nobody else sees the
   owner's. Choosing where a note goes is a security decision, not filing.
5. **Captures go to one inbox.** A curator agent routes each item to the right vault, splitting items
   that mix scopes.
6. **No secrets in any vault.**

The full set, with the ingest / query / lint operations, is in [`example/AGENTS.md`](example/AGENTS.md)
and [`skills/vault-wiki/SKILL.md`](skills/vault-wiki/SKILL.md). An optional permission taxonomy
(`company_private`, `customer_private`, `deidentified_reusable`, `public`…) and the de-identification
bridge between client data and reusable knowledge are described in
[`example/company/wiki/resources/knowledge-permissions.md`](example/company/wiki/resources/knowledge-permissions.md).

## Quick start

Requirements: git, Python 3.11+ for the linter.

```bash
git clone <this repo> agent-maintained-vault
cp -r agent-maintained-vault/example my-workspace
cd my-workspace
rm -rf clients/acme-bakery      # drop the fictional client
```

Then:

1. Edit `AGENTS.md`, `vaults.toml` and each vault's `AGENTS.md` for your company.
2. Make each vault its own git repository (`git init` inside `company/`, `owner/`,
   `clients/<slug>/`) and push each to a private remote with its own access list.
3. Point your agents at the workspace `AGENTS.md`, and install the skill: copy or symlink
   `skills/vault-wiki/` into your agent's skills folder (for Claude Code, `~/.claude/skills/`).
4. Open the workspace folder in Obsidian if you want a human view.

New client vault:

```bash
python3 path/to/tools/vaultctl.py new clients/globex --name "Globex"
# then add the printed entry to vaults.toml, by pull request
```

## vaultctl

```bash
python3 tools/vaultctl.py check <workspace>   # every vault in vaults.toml + cross-vault leaks
python3 tools/vaultctl.py lint <vault>        # one vault
python3 tools/vaultctl.py log <vault> ingest "Kickoff transcript" --body "Created [[order-assistant]]."
```

`check` and `lint` report:

- missing `AGENTS.md`, `index.md`, `log.md`, `raw/` or `wiki/`
- canon pages without `status`, `canonical`, `last_verified`, `review_cadence`, and canons past their review date
- broken `[[wikilinks]]` and relative Markdown links (code blocks ignored)
- wiki pages missing from `index.md`
- malformed or out-of-order `log.md` headings
- unknown `knowledge_permission` values, superseded pages outside `wiki/_archive/`
- strings that look like secrets (private keys, AWS, GitHub, Slack, Telegram, `sk-` API keys)
- **scope leaks**: a term listed in one vault's `private_terms` appearing in another vault
- with `--since <git ref>`: files in `raw/` modified or deleted (moves are fine), and canon changes flagged for human approval

Exit code is 1 on errors (or on warnings with `--strict`), so it fits a pre-commit hook or CI.
Example run after a client contact's name slipped into the company vault:

```
$ python3 tools/vaultctl.py check example --today 2026-01-25
error company/raw/2026-01-06-strategy-call-notes.md: scope leak: private term of vault 'acme-bakery'

1 error(s), 0 warning(s)
```

## Enforcing canon review

The linter flags canon changes; your git host enforces them. On each vault repository, protect the
default branch, require one approving review, and add a `CODEOWNERS` file:

```
/AGENTS.md      @your-handle
/CLAUDE.md      @your-handle
/wiki/canon/    @your-handle
/skills/        @your-handle
```

Agents then commit wiki pages freely on their own branches and open a pull request whenever a canon
moves.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 tools/vaultctl.py check example --today 2026-01-25
```

`--today` pins the date so the example canons are not reported as overdue.

## Limitations

- **The linter checks form, not meaning.** It cannot tell that a wiki page contradicts a canon or that a
  figure was copied out of one; the nightly lint in the skill leaves that to an agent's judgement.
- **Leak detection is term-based.** It only catches the words you list in `private_terms`.
- **The frontmatter parser is minimal**: top-level `key: value` pairs only, no full YAML.
- **No sync or automation is included.** How agents commit (directly, on branches, or through a
  scheduled sync job) depends on your setup.
- **Wikilink resolution approximates Obsidian's**: path from the vault root, file name, or path suffix.

## License

MIT, see [LICENSE](LICENSE).

## About

Built by Loic Guyon at AI Jungle — https://www.welcometotheaijungle.com
