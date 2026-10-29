---
title: Agent memory
type: resource
status: active
knowledge_permission: personal_private
---

# Agent memory

Shared by every agent on every machine (symlink each agent's memory folder here).
One file per lesson, named `feedback-<topic>.md` (a correction from a human) or
`reference-<topic>.md` (where something lives, how a tool behaves). Each file states the rule,
why it exists, and how to apply it. Agents read the relevant files before acting.

Example: [[feedback-verify-before-assuming]].
