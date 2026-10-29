# Vault: Acme Bakery (schema, read before writing)

Client vault for **Acme Bakery** (fictional), a three-shop bakery. Workspace rules in `../../AGENTS.md` apply.

## Scope

- **Here**: everything produced for or received from Acme Bakery: documents, meeting transcripts,
  projects, deliverables, and the facts of the engagement (canon).
- **Never here**: another client, the company's internal economics, personal material.
  For a company fact, refer to the company vault by page title without copying it.

## Structure

| Path | Role | Who writes |
|---|---|---|
| `raw/` | documents received, transcripts, exports | append only |
| `wiki/canon/` | engagement facts: scope, contacts, dates (`CANON-*.md`) | pull request only |
| `wiki/projects/` | work in progress | agents |
| `wiki/deliverables/` | what was sent to the client, as sent | agents |

Default permission: `customer_private`.
