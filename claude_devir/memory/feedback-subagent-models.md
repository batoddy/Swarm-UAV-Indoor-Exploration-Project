---
name: feedback-subagent-models
description: Run background subagents on sonnet or opus, not on the most expensive model
metadata:
  type: feedback
---

User: "arka planda sonnet falan çalışsın ... fable dan harcama" / "opus veya" (2026-11-11).

**Why:** Cost: background work shouldn't use the most expensive model.

**How to apply:** When spawning subagents, set model to sonnet (mechanical work) or opus (writing code/design).
