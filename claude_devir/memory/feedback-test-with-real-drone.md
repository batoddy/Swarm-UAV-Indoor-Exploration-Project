---
name: feedback-test-with-real-drone
description: Keep fake-drone/synthetic tests of Tello code short; real-drone testing is done by the user
metadata:
  node_type: memory
  type: feedback
  originSessionId: c0efccba-7400-47c8-83e9-4a8bd1016dae
  modified: 2026-11-11T07:22:47.541Z
---

Fake-drone or synthetic tests of Tello code are OK when a test is really needed, but keep them short — don't spend long on them. The user will also test on the real drone, so list what needs real-drone checking.

**Why:** User first objected to repeated fake-drone runs ("fake dron uçurup durma ... test lazımsa söyle gerçeğini bağlayayım"), then clarified (2026-11-11): "test lazımsa et yine sahte dronda da çok kasma yani gerçekte de test yaparız".

**How to apply:** One quick sanity run at most; no elaborate simulations. Related: [[feedback-answer-questions-directly]]
