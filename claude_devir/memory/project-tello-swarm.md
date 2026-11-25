---
name: project-tello-swarm
description: Goal is autonomous indoor exploration with 3 Tello EDU drones; localization in separate ROS 2 nodes on Ubuntu; tellolink is the lowest-level interface
metadata:
  type: project
---

The user's goal (stated 2026-11-11): a swarm of 3 Tello EDU drones doing autonomous indoor exploration. Localization (VO/VIO/VSLAM) and swarm logic run as separate ROS 2 nodes on Ubuntu. The `tellolink` library (github.com/batoddy/tellolink, Apache 2.0, derived from TelloPy) only connects, sends commands and exposes the drone's data; the next step is a ROS 2 publisher on top of it, not inside it.

**Why:** The user wants a clean split: driver library ↔ ROS nodes ↔ odometry.

**How to apply:** Keep ROS, odometry and swarm code out of tellolink. One Tello object per drone, one Wi-Fi adapter per drone (`local_ip`). Related: [[feedback-minimal-library]]
