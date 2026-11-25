---
name: feedback-no-unrequested-data-sources
description: Visual odometry must be image-only unless the user approves other inputs; ask before mixing in Tello telemetry
metadata:
  node_type: memory
  type: feedback
  originSessionId: c0efccba-7400-47c8-83e9-4a8bd1016dae
  modified: 2026-10-28T17:03:50.189Z
---

User wants visual odometry to use only camera images. I had silently used Tello telemetry (vgx/vgy/vgz for scale, takeoff state for start frame) and the user objected: "ben sadece visual odom yapmanı istiyordum" (2026-10-28).

**Why:** The project goal is pure VO; mixing sensor data hides how well vision alone works.

**How to apply:** Before using any non-image data source (telemetry, SDK state, IMU) in VO/SLAM code, state it explicitly and get approval, or make it clearly optional. Related: [[feedback-answer-questions-directly]]
