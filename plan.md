# Plan — Physical Fidelity & Sim-to-Real Validation (Phase PF)

Goal of this phase: stop trusting the sim blindly. Add the real hardware
*constraints* to the MuJoCo model, then *measure the margins* so we can answer
one question per task: **"could the real H1 actually do this without
saturating, overheating, tipping, or running out of battery?"**

This phase is independent of Phase 8 (manipulation) but should land before or
alongside it — there's no point training a policy that commands torques no real
motor can hold. PF-8 also reframes the Phase 8 tasks to stay honest to the
base H1's real capabilities.

Status key: [ ] not started · [~] in progress · [x] complete · [!] blocked
Work top-to-bottom. After each item, mark [x] and update PROGRESS.md.
Behavior rules from CLAUDE.md still apply: never delete working code (use
`_old` suffix), commit after each item (`feat: <desc>`), don't gold-plate.

---

## Reference numbers (single source of truth)

Pulled from Unitree H1 published specs. Hard numbers are public; anything
marked ASSUMPTION is not published and must be logged as such in PROGRESS.md.

| Quantity                  | Value                          | Source         |
|---------------------------|--------------------------------|----------------|
| Total mass                | ~47 kg                         | published      |
| Height                    | ~1.8 m                         | published      |
| DOF                       | 19 (4 per arm, no hands)       | published      |
| Knee peak torque          | ~360 N·m                       | published      |
| Hip peak torque           | ~220 N·m                       | published      |
| Waist (torso) peak torque | ~220 N·m                       | published      |
| Ankle peak torque         | ~45–59 N·m                     | published      |
| Arm joint peak torque     | ~75 N·m (base H1)              | published      |
| Battery                   | 864 Wh, 15 Ah, 67.2 V max      | published      |
| Continuous payload        | ~10–15 kg                      | published est. |
| Joint velocity limits     | read from MJCF/URDF, don't guess | model        |
| Continuous torque rating  | ASSUME 35% of peak (placeholder) | NOT published |
| Gear ratio / rotor inertia| read from MJCF if present, else ASSUMPTION | NOT published |

Key honesty note: base H1 has **4-DOF arms and no hands** — it physically
cannot grasp. All "manipulation" must be modeled as pushing, or explicitly
flagged as "assumes Dex5 hand add-on (≤2 kg payload)". See PF-8.

Open-source references (for cross-checking model values):
- `mujoco_menagerie/unitree_h1` — MJCF, masses/inertias/limits (BSD-3)
- `unitree_ros` — URDF with mass/inertia/limit data
- `unitree_mujoco` — sim-to-real bridge, motor numbering matches hardware
- Berkeley Humanoid Lite (`HybridRobotics/Berkeley-Humanoid-Lite`) — a fully
  open hardware+firmware+software stack, useful as a reference for what a
  complete physical model looks like (smaller/weaker robot, don't copy specs)

Joint order (from CLAUDE.md, index 0–18):
left_hip_yaw, left_hip_roll, left_hip_pitch, left_knee, left_ankle,
right_hip_yaw, right_hip_roll, right_hip_pitch, right_knee, right_ankle,
torso, left_shoulder_pitch, left_shoulder_roll, left_elbow,
right_shoulder_pitch, right_shoulder_roll, right_elbow,
left_wrist_roll, right_wrist_roll

---

## Tasks

- [ ] **PF-0** Spec config: single source of truth for all real numbers.
- [ ] **PF-1** Actuator torque/velocity clamps + saturation logging.
- [ ] **PF-2** Power & energy budget (instantaneous + average → runtime est).
- [ ] **PF-3** Thermal duty-cycle check (RMS torque vs continuous rating).
- [ ] **PF-4** Control-loop realism (policy rate, latency, sensor noise).
- [ ] **PF-5** Contact/friction realism + domain-randomization toggle.
- [ ] **PF-6** Stability & payload feasibility (CoM/support polygon, arm moment).
- [ ] **PF-7** Feasibility report — aggregate per-task "can it handle it" readout.
- [ ] **PF-8** Task honesty reframing — base H1 has no hands; push-based tasks.
- [ ] **PF-9** (stretch) Berkeley Humanoid Lite cross-check.

---

# PROMPTS

Run in order. Each is self-contained — paste exactly into Claude.

---

## PROMPT PF-0 — Spec config

```
Read CLAUDE.md, GOALS.md, and PROGRESS.md before starting. This is task PF-0.

Create src/backend/h1_specs.py: a single source of truth for the real Unitree
H1 hardware numbers, so every later physical-fidelity check imports from here
instead of hardcoding.

Include, in the joint order defined in CLAUDE.md (19 joints):
- PEAK_TORQUE_NM per joint: knee ~360, hip (yaw/roll/pitch) ~220, ankle ~45-59,
  torso/waist ~220, shoulder/elbow/wrist (arm joints) ~75.
- CONTINUOUS_TORQUE_NM per joint: set to 0.35 * peak as a PLACEHOLDER. Add a
  comment that this is an ASSUMPTION — Unitree does not publish continuous
  ratings — and log this assumption in PROGRESS.md.
- VELOCITY_LIMIT_RAD_S per joint: read these from the MJCF/URDF if present
  (mujoco_menagerie unitree_h1). Do NOT invent them. If absent, mark as
  ASSUMPTION and use a conservative default.
- MASS_KG = 47, HEIGHT_M = 1.8, NUM_DOF = 19, ARM_DOF_PER_SIDE = 4, HAS_HANDS = False.
- BATTERY_WH = 864, BATTERY_V_MAX = 67.2, BATTERY_AH = 15.
- CONTINUOUS_PAYLOAD_KG = (10, 15).

Add a one-line module docstring linking to the source. Mark PF-0 complete in
plan.md and update PROGRESS.md.
```

---

## PROMPT PF-1 — Actuator clamps + saturation logging

```
Read CLAUDE.md, GOALS.md, PROGRESS.md, and plan.md before starting. This is
task PF-1. Import limits from src/backend/h1_specs.py (do not hardcode).

In h1_env.py (the base env), the actuators are currently treated near-ideally.
Make them physical:

1. Before applying any control torque each step, CLAMP it to that joint's
   PEAK_TORQUE_NM (both directions). Also clamp commanded joint velocity to
   VELOCITY_LIMIT_RAD_S. Set the corresponding MJCF forcerange/ctrlrange so the
   physics engine enforces the same limits — don't only clamp in Python.

2. Add a SaturationLogger (new file src/backend/physical/saturation.py) that,
   per joint per episode, records: peak |torque|, fraction of peak rating used,
   count of steps where torque was within 2% of the limit (saturation events),
   and same for velocity. Reset on env reset.

3. Expose a get_saturation_report() returning a per-joint dict. Print a compact
   summary at episode end.

4. Keep the old actuation path as _apply_control_old() for reference (don't
   delete working code).

Test: run one episode of the current policy and confirm the report prints and
flags any joint above ~80% of peak. Mark PF-1 complete in plan.md, commit
`feat: physical actuator clamps + saturation logging`, update PROGRESS.md.
```

---

## PROMPT PF-2 — Power & energy budget

```
Read CLAUDE.md, GOALS.md, PROGRESS.md, and plan.md. This is task PF-2. Import
from src/backend/h1_specs.py.

Add power accounting to the physical layer (extend src/backend/physical/, e.g.
power.py):

1. Each step, compute mechanical power per joint = torque * joint_velocity, and
   total = sum over joints. Track instantaneous peak total power and the
   running mean total power over the episode.

2. Estimate electrical draw simply: P_elec = P_mech / EFFICIENCY, with
   EFFICIENCY = 0.7 as an ASSUMPTION (log it in PROGRESS.md). Add negative
   mechanical power (regen) as zero contribution — don't assume regen recovery.

3. From mean P_elec and BATTERY_WH, compute estimated runtime in minutes for
   sustained execution of this task. Add to the report from PF-1 as a
   "power" section: peak_power_w, mean_power_w, est_runtime_min.

Test: run an episode, confirm runtime estimate is plausible (H1 real-world is
~1.5-2 hr for moderate activity; a hard task should come out lower). Mark PF-2
complete in plan.md, commit, update PROGRESS.md.
```

---

## PROMPT PF-3 — Thermal duty-cycle check

```
Read CLAUDE.md, GOALS.md, PROGRESS.md, and plan.md. This is task PF-3. Import
from src/backend/h1_specs.py.

MuJoCo does not model heat, so this is a post-hoc duty-cycle check. The risk
is sustained near-peak torque: peak (360 N·m) is fine for a moment, deadly if
held.

In src/backend/physical/thermal.py:

1. Over a sliding window (default 2 s of sim time), compute RMS torque per
   joint.

2. Compare RMS torque to CONTINUOUS_TORQUE_NM (the PF-0 placeholder). Flag any
   joint whose windowed RMS exceeds its continuous rating as a THERMAL RISK,
   with the duration it stayed over.

3. Add a "thermal" section to the report: per-joint max windowed RMS, % of
   continuous rating, and a boolean overheat_risk.

Add a clear caveat in the report output: continuous ratings are assumptions,
not published, so treat this as a relative warning not an absolute. Test on one
episode. Mark PF-3 complete in plan.md, commit, update PROGRESS.md.
```

---

## PROMPT PF-4 — Control-loop realism

```
Read CLAUDE.md, GOALS.md, PROGRESS.md, and plan.md. This is task PF-4.

This is the layer that actually decides sim-to-real transfer. Add to h1_env.py
(behind a config flag REALISM_ENABLED so we can A/B it):

1. Decouple policy rate from physics rate: policy acts at POLICY_HZ (default 50)
   while MuJoCo steps at its native rate; hold the last action between policy
   steps (zero-order hold).

2. Actuator latency: buffer commanded torques by ACTUATOR_LATENCY_MS
   (default 10 ms) before they reach the actuators.

3. Observation noise + latency: add Gaussian noise to IMU (base ang/lin vel,
   projected gravity) and joint encoders, and delay observations by
   OBS_LATENCY_MS (default 5 ms). Put noise sigmas in a config dict with sane
   defaults; mark them ASSUMPTION in PROGRESS.md.

Keep all magnitudes in one config block so they're easy to tune. Test: confirm
a policy trained without realism degrades measurably with REALISM_ENABLED=True
(this gap IS the sim-to-real risk and is the point). Mark PF-4 complete in
plan.md, commit, update PROGRESS.md.
```

---

## PROMPT PF-5 — Contact/friction realism + domain randomization

```
Read CLAUDE.md, GOALS.md, PROGRESS.md, and plan.md. This is task PF-5.

For any pushing/carrying task, contact and friction decide whether the behavior
transfers. In h1_env.py / the MJCF:

1. Expose friction coefficients for foot-floor, hand-object, and object-floor
   contacts as named config values. Set reasonable defaults and document them.

2. Add a domain_randomization() hook (off by default) that, per episode,
   samples friction, object mass (within a configured range), and a small
   payload mass offset. This is standard sim-to-real hardening.

3. Tune contact solver params (solref/solimp) on object contacts to avoid
   penetration/jitter; document chosen values.

Test: with randomization on, run 5 episodes and confirm friction/mass vary per
episode and the sim stays stable (no exploding contacts). Mark PF-5 complete in
plan.md, commit, update PROGRESS.md.
```

---

## PROMPT PF-6 — Stability & payload feasibility

```
Read CLAUDE.md, GOALS.md, PROGRESS.md, and plan.md. This is task PF-6. Import
from src/backend/h1_specs.py.

In src/backend/physical/stability.py:

1. Each step, compute the robot center of mass and the support polygon (convex
   hull of foot contact points). Flag steps where the CoM ground projection
   leaves the support polygon (tipping risk). Report max margin and # of
   violations per episode.

2. Payload check: when the robot carries an object, compute the static moment
   at the shoulder (object_mass * g * horizontal_arm_extension) and compare to
   the arm joint peak torque (~75 N·m). Flag if it exceeds, say, 60% of rating
   (leave headroom for dynamics).

3. Also flag if total carried mass exceeds CONTINUOUS_PAYLOAD_KG range.

Add a "stability" section to the report: tipping_violations, min_support_margin,
shoulder_moment_pct_of_limit, payload_ok. Test on a carry task. Mark PF-6
complete in plan.md, commit, update PROGRESS.md.
```

---

## PROMPT PF-7 — Feasibility report

```
Read CLAUDE.md, GOALS.md, PROGRESS.md, and plan.md. This is task PF-7.

Aggregate PF-1 through PF-6 into one verdict per task run.

1. src/backend/physical/feasibility.py: collect saturation, power, thermal, and
   stability sections into a single FeasibilityReport with an overall verdict:
   FEASIBLE / MARGINAL / INFEASIBLE, derived from simple rules (e.g.
   INFEASIBLE if any joint saturates >X% of steps, overheat_risk True, tipping
   violations >0, or payload over limit). Document the thresholds.

2. Save the report as JSON per run under src/backend/checkpoints/<ckpt>/feasibility/.

3. Surface it live: extend the WebSocket frame with a "feasibility" object
   (verdict + the worst-offending joint + a one-line reason). Update the
   WebSocket contract section in CLAUDE.md to document the new field.

4. Frontend: in scoring.js / the status bar, show a feasibility badge —
   green FEASIBLE, amber MARGINAL, red INFEASIBLE — with a tooltip giving the
   reason. This makes the "can the real hardware do it" answer visible during
   the demo, which is a strong judging moment.

Test end-to-end: run a task, confirm the badge updates and JSON is written.
Mark PF-7 complete in plan.md, commit, update PROGRESS.md.
```

---

## PROMPT PF-8 — Task honesty reframing (no hands on base H1)

```
Read CLAUDE.md, GOALS.md, PROGRESS.md, and plan.md. This is task PF-8.

The base H1 has 4-DOF arms and NO hands — it cannot grasp. The Phase 8 tasks
(box_sort, table_setup, package_delivery) imply grasping, which is not
physically real for this robot. Make them honest:

1. Add a capability flag in h1_specs.py: HAS_HANDS = False, and a separate
   ASSUMES_DEX5_HAND config that a task can opt into (Dex5: ~2 kg payload).

2. For HAS_HANDS = False: reframe each task as PUSH-based. box_sort and
   table_setup become "push object to target zone with arm/body contact" — no
   grasp. package_delivery either (a) becomes a push-and-shepherd task, or
   (b) requires ASSUMES_DEX5_HAND = True and caps object mass at 2 kg, clearly
   labeled in the task intro overlay (Phase 9.1) as "assumes Dex5 hand".

3. Update the task env reward logic accordingly (reach + push contact, not
   grasp) and note the change in each task file's docstring.

4. Add a one-line note to each task's "Real World Context" entry (Phase 9.3)
   distinguishing what base H1 can do vs what needs a hand add-on.

Do NOT silently fake grasping. The whole value of this phase is honesty about
hardware. Mark PF-8 complete in plan.md, commit, update PROGRESS.md.
```

---

## PROMPT PF-9 — (stretch) Berkeley Humanoid Lite cross-check

```
Read CLAUDE.md, GOALS.md, PROGRESS.md, and plan.md. This is task PF-9 (stretch,
skip if time-constrained).

As a sanity check on our physical model, compare against a fully open-source
humanoid whose real specs are public end-to-end: Berkeley Humanoid Lite
(HybridRobotics/Berkeley-Humanoid-Lite, arXiv 2504.17249).

1. Write a short docs/physical_validation.md noting how our H1 feasibility
   thresholds (torque headroom %, duty-cycle rule, payload margin) compare in
   spirit to a robot with fully published hardware. This is a credibility note
   for judges, not a code change.

2. Optionally add a second spec profile (berkeley_lite_specs.py) so the
   feasibility tooling can be pointed at a different robot — demonstrates the
   tooling generalizes.

Mark PF-9 complete in plan.md, commit, update PROGRESS.md.
```
