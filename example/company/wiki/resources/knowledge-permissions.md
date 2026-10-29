---
title: Knowledge permissions
type: resource
status: active
knowledge_permission: deidentified_reusable
---

# Knowledge permissions

Every page that may leave its vault (search index, deliverable, public post) carries one class in
its `knowledge_permission` frontmatter field.

| Class | Meaning | Approval |
|---|---|---|
| `personal_private` | the owner's personal material; lives in the owner vault only | n/a |
| `company_private` | internal to the company | agents may curate autonomously |
| `customer_private` | one client's material; lives in that client's vault only | n/a |
| `customer_visible` | safe to show that client | human approval |
| `deidentified_reusable` | a pattern stripped of client identity, reusable across clients | human review when derived from client data |
| `public` | public sources, or material approved for publication | human approval before publishing |

## The only bridge

Client data never flows straight into reusable company knowledge:

`customer_private` → human-approved de-identification → `deidentified_reusable` → company methods and templates.

## What agents may do alone

Curate `company_private` pages. Everything that becomes visible to a client or the public, touches
money, legal or pricing, deletes a source, or crosses the bridge above waits for a human.
