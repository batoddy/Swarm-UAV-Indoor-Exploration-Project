---
name: feedback-answer-questions-directly
description: "When the user asks a plain question, answer it directly; don't run experiments or tests unasked"
metadata:
  node_type: memory
  type: feedback
  originSessionId: c0efccba-7400-47c8-83e9-4a8bd1016dae
  modified: 2026-10-28T17:03:46.015Z
---

When the user asks a knowledge question (e.g. "optik akışta kaç nokta iyi sonuç verir?"), answer it directly from knowledge. Do not launch benchmark runs or parameter sweeps on their data unless they ask.

**Why:** User interrupted a parameter sweep with "hayır tek tek deneme basit bir soru sordum" (2026-10-28).

**How to apply:** Give the short answer first; offer an empirical test in one line only if it adds real value. Related: [[feedback-no-unrequested-data-sources]]
