---
name: feedback-minimal-library
description: tellolink must stay minimal; don't add features, layers or settings the user didn't ask for; propose and ask instead
metadata:
  type: feedback
---

The user rejected a first design with time correction, ROS-ready messages and extras: "en alt seviye arayüz olacak, hiçbir ek ayar istemiyorum ... bildiğin en basic kütüphane" (2026-11-11). Event design went through several rounds; the final choice is TelloPy-style per-type events (`subscribe(EVENT_X, handler(drone, data))`) plus latest-value attributes (`drone.imu`, ...).

**Why:** The library is the lowest layer; everything else belongs to the user's own code / ROS nodes.

**How to apply:** Add only what is asked. For design questions, give one recommendation with reasons and let the user decide; don't reopen settled design choices without a concrete reason. Related: [[project-tello-swarm]]
