# Project context (handoff from the Windows session, 2026-11-11)

This file is not part of the public repo (it is excluded locally). It carries over what was learned in a long session on Windows, so work can continue on Ubuntu. Detailed references are in `claude_devir_notes/`:
- `TELLO_VERI_RAPORU.md` (Turkish): every Tello packet/record, byte offsets, units, rates, how each was verified, the TelloPy bugs found.
- `TELLO_KUTUPHANE_TASARIM.md` (Turkish): the original design note for tellolink (partly superseded, see below).

## The user and how to work with them

- **Reply in Turkish.** Code, comments, commit messages and the repo's non-README files are in English. The README is Turkish for now; it will be translated to English later.
- Plain question → plain, direct answer. No unrequested experiments or test runs.
- Fake-drone / synthetic tests only when really needed, and short. The user tests on the real drone; list what needs real-drone checking.
- When spawning subagents, use **sonnet or opus**, not the most expensive model.
- The user wants this library **minimal** ("the most basic library"). Do not add features, layers or settings they did not ask for. When unsure, propose and ask.
- Before mixing Tello telemetry into visual odometry code, ask (an earlier VO project was meant to be image-only).
- Commit/push only when asked.

## Goal

Autonomous indoor exploration with a swarm of **3 Tello EDU** drones. Localization (VO/VIO/VSLAM) and swarm logic will run as **separate ROS 2 nodes on Ubuntu**. `tellolink` is only the lowest-level interface: connect, send commands, expose everything the drone sends. **Next step: a ROS 2 publisher node built on top of tellolink** (not inside the library). Each drone gets its own `Tello` object (and probably its own node/process).

## tellolink in short

Files: `tello.py` (sockets, threads, commands, events), `protocol.py` (packet/record decoding, dataclasses), `example.py` (connect and print, `--fly` to take off), `keyboard_control.py` (pygame: WASD/arrows, T/L, F flip, 1–6 speeds, I data panel), `tests/`.

- `Tello(local_ip=None)`; `connect(timeout)`, `close()`, `takeoff()`, `land()`, `emergency()`, `flip(direction)`, `set_sticks(pitch, roll, yaw, throttle)` (−1..1, held until changed), `set_altitude_limit`, `set_low_battery_threshold`, `set_wifi_name`, `set_wifi_password`.
- Latest values as attributes: `drone.status, imu, gyro, mvo, tof, nav, osd, sticks, attitude_target, motors, battery, wifi, frame`, `drone.unsolved[record_id]`.
- Events: `drone.subscribe(drone.EVENT_IMU, handler)`, `handler(drone, data)`. The record is written to the attribute first, then the event fires. One event per record type (a log packet carries records of different rates). `EVENT_CONNECTED/DISCONNECTED`, `EVENT_UNSOLVED` (undecoded records, raw payload), `EVENT_FRAME`.
- Threads: data events run in the receive thread; `EVENT_FRAME` in the video-decode thread (PyAV, frames fed one by one so each keeps its own `recv_time`). Handlers must be short; heavy work → `queue.Queue`.
- No time correction: records carry `recv_time` (host `time.monotonic()`) and `tick` (drone counter). Frames have no tick.
- Design history: the user rejected (1) read_x_new queues, (2) a single per-packet callback, and finally chose TelloPy-style per-type events + latest-value attributes. Don't reopen this without a reason.

## Verified facts (real flights; see the report for detail)

- **Velocities and positions are in a WORLD frame, not the body frame**: x = yaw 0° direction, y = yaw +90°, z down. Applies to `status`, `imu.vel_*`, `imu.lin_acc_*`, `nav`, `mvo`, `osd`. Raw `imu.acc_*` (in g, z ≈ −1 at rest) and `imu.gyro_*` are body frame (x fwd, y right, z down). Found on the 3rd flight (yaw 80°); the first two flights had yaw ≈ −12° and had misled us into "x forward, y right". Body velocity = rotate world vx, vy by −yaw.
- Euler from `imu.q0..q3` (q0 = w, standard ZYX) matches the drone's own `osd` angles within 0.1°. Signs: roll right-down +, pitch nose-up +, yaw clockwise from above +.
- Yaw has no compass (Tello has none); its zero is the drone's choice, probably heading at power-on (NOT verified; test: power on, rotate by hand 90°, read yaw).
- Rates: status 10, imu 10, nav 10, mvo 5, tof 5, battery 5, sticks 5, osd ~1.7, gyro 20 (motors on), motors 10 (motors on), attitude_target 2.5 (motors on), wifi 1, video ~29–32 fps 960×720 (decode ~7 ms, first frame ~2 s after connect).
- Tick ≈ 2,343,850 Hz (nominal 2,344,062).
- On connect the drone may send a few **stale IMU records** from power-on (quaternion all 0, measured 70–110 s earlier). Undecided whether tellolink should drop them (user not asked yet).
- The stick values the drone reports are 0.90–0.97 × what was sent.
- Log records appeared ~1.1–1.6 s "late" relative to stick send times (tick mapping); not investigated.
- Once, ~1 s after connect, the log stream had a 2 s gap (tick gap too); never during flight.
- Motor order inferred (not verified physically): front-right, front-left, rear-left, rear-right.
- `status.em_ground` does NOT mean "on the ground" (only ~0.5 s at motor start). Use `em_sky`/`em_open` or `sticks.motors_on`.
- Light byte is always 0 on this firmware (not read). Wi-Fi second byte always 0.

## Multi-drone

Each Tello is its own AP at 192.168.10.1 → one Wi-Fi adapter per drone; pass the adapter's IP as `local_ip`. On Linux all adapters are in the same subnet, so binding to an address may not be enough (`SO_BINDTODEVICE` may be needed). **Untested.** EDU "station mode" is not an option: it has no flight log or the video path used here.

## ROS 2 notes (for the next step)

- World frame here is x = yaw0, y = yaw+90, z down (NED-like). ROS REP-103 `odom` is x forward, y left, z up → negate y and z (and convert the quaternion accordingly).
- Stamps: `recv_time` is jittery (Wi-Fi). For IMU-grade stamps, map `tick` to host time with a line fit (the old TelloPy `estimator.py` did this: per-packet freshest record, least squares over 60 s, outlier rejection). Frames only have `recv_time`.
- Three drones = three independent frames (different yaw zero and origin); merging needs each drone's initial pose.

## Open items

- README → English (later).
- Tests compare against TelloPy using flight recordings that are not in the repo (`ROOT = parents[2] / 'kayitlar'`); on Ubuntu they will be skipped/fail. Decide later whether to add small recordings under `tests/data/`.
- Not yet tried on a real drone: `flip`, Wi-Fi settings, altitude/low-battery settings, several drones at once.
- Records tellolink delivers as `unsolved`: 1001, 1306, 2208 (meaning known: aircraft state, control outputs, second attitude; decoded in TelloPy, not yet in tellolink) and 1002, 1200, 1202, 1203, 1300, 1303, 10085, 10086, 10100 (meaning partly or not known). See the report §4.5–4.7.
- License: Apache 2.0, NOTICE credits TelloPy (Hanyazou). Keep that if code moves.
