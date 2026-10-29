# Vault: Owner (schema, read before writing)

Owner only. Never shared with a partner or a client. Workspace rules in `../AGENTS.md` apply.

## Scope

- **Here**: the inbox, the journal, the agents' shared memory, personal admin (household, health, personal finances).
- **Not here**: anything a partner or a client should ever read.

## Structure

| Path | Role | Who writes |
|---|---|---|
| `raw/inbox/` | every capture lands here first (voice notes, clippings, forwarded mail) | anyone; the curator empties it |
| `raw/journal/` | dailies and session handoffs; history, never current truth | agents and the owner |
| `wiki/agent-memory/` | memory shared by every agent on every machine (one file per lesson learned) | agents |
| `wiki/canon/` | personal facts that change (addresses, contracts, renewals) | pull request only |

## Inbox routing

For each item in `raw/inbox/`: decide the vault (named client → that client's vault; company matter →
`company/`; personal → stays here; doubt → leave it and flag it), move the file as-is into that vault's
`raw/`, then ingest it there. Automatic runs only take items older than 7 days, 5 per run.
