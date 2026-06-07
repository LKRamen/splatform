# Progress Log

## How to use this file
At the end of every work block, append a new session entry below.
The next session MUST read the most recent entry before doing anything.

---

## Session 0 — Project initialized
**Date**: 2025-06-07 (night before hackathon)
**Status**: Files created, no code written yet.

### What exists
- `CLAUDE.md` — full project spec, stack, contracts, scoring rubric
- `GOALS.md` — 7 phases, 25 goal items, ordered
- `PROGRESS.md` — this file
- `src/`, `assets/` directory structure created

### What does NOT exist yet
- No Python code
- No frontend code
- No MuJoCo Menagerie clone
- No H1 GLB asset
- No splat file (captured tomorrow morning at Fordham)

### Next session must start here
Read GOALS.md. Begin at **Goal 1.1**. Do not skip ahead.

### Known decisions made before coding started
- Stack is finalized: MuJoCo + SB3 PPO + FastAPI WS + Three.js
- H1 joint order is locked (see CLAUDE.md)
- Observation space is 47-dim (see CLAUDE.md)
- Splat file won't exist until morning — all code must gracefully handle its absence
- If `assets/h1.glb` is missing, frontend shows capsule placeholder — do not block on asset

### Blockers
None yet.

---

<!-- New sessions: append below this line -->

## Session — Phase 7 visual fixes (run-plan PROMPTS.md)
**Date**: 2026-06-07

### 7.A — Robot mesh fixed (complete)
- Replaced the floating-chunks GLB rendering in `src/frontend/viewer.js`.
- Added `buildProceduralRobot()`: a clean teal (#00e5cc) humanoid built from
  `CapsuleGeometry`/`BoxGeometry` with a correct parent-child hierarchy
  (torso root → head, upper_arm→forearm→hand ×2, thigh→shin→foot ×2). Each
  segment is a named `THREE.Object3D` pivot with a mesh child offset so limbs
  extend away from the joint. H1 proportions (~1.8 m).
- `JOINT_TARGETS` maps all 19 stream joints (CLAUDE.md order) to the correct
  segment + local rotation axis (hip yaw=Y/roll=Z/pitch=X, knee/ankle/elbow=X,
  shoulder pitch=X/roll=Z, wrist=Y, torso=Y).
- Fixed `JOINT_NAMES` to match CLAUDE.md exactly (was `shoulder_yaw`, now
  `wrist_roll`).
- GLB path kept: only used if the loaded GLB has a `SkinnedMesh` with bones;
  otherwise falls back to the procedural rig. Chosen path logged to console.
- Old `buildCapsulePlaceholder` preserved as `buildCapsulePlaceholder_old`.

### 7.B — Indoor lobby fallback (complete)
- Replaced the NYC-buildings procedural scene with `buildLobby()` in
  `viewer.js`, returned as a single toggleable `THREE.Group` (`lobbyGroup`).
- Atrium: dark floor + grid, ceiling plane at y=4.5 with a subtle grid, four
  walls at x/z=±12 (each with three tall emissive-blue window openings facing
  inward), four structural columns at (±8, ±8), and three warm emissive
  ceiling panels backed by soft point lights. No more black void.
- Old NYC builder preserved as `buildProceduralScene_old`.

### 7.C — Splat pipeline + indicator (complete)
- Rewrote the splat loader to use the real `@mkkellogg/gaussian-splats-3d`
  API (`DropInViewer.addSplatScene`, which extends `THREE.Group` and renders
  inside our existing loop). The previous code imported a non-existent
  `GaussianSplatMesh` export and never actually loaded.
- HEAD-checks `assets/scene.splat` first; on present file it imports the lib
  and streams the splat, updating the centered overlay
  "Loading Fordham splat... X%" via `onProgress` (0–100).
- On success: hides `lobbyGroup`, adds the splat, logs
  "Splat loaded successfully", sets the status-bar indicator to teal
  "● Live Splat".
- On missing/failed load: keeps the lobby visible, logs
  "Splat not found, using procedural fallback", indicator stays gray
  "● Procedural".
- Added `#scene-indicator` to the status bar in `index.html`, next to the
  connection dot.

### Robot swap — H1 → Unitree G1 (29 DOF)
- Switched the simulated robot from H1 (19 DOF) to the Menagerie Unitree G1
  (`unitree_g1/g1.xml`, 29 DOF, standing pelvis height 0.79 m).
- New `src/backend/g1_env.py` (`G1TraversalEnv`): same traversal logic as the
  H1 env but loads g1.xml and **derives obs/action dims from the model**
  (`model.nu`), so contracts auto-size. Observation is now 67-dim
  (29 joint_pos + 29 joint_vel + 3 lin_vel + 3 proj_grav + 2 goal_vec +
  1 goal_dist); action is 29-dim. `h1_env.py` retained (retired) per the
  never-delete rule.
- `server.py` imports `G1TraversalEnv`; WS frame `joints` slice is now
  `qpos[7:7+n_joints]` (model-derived, was hard-coded `[7:26]`).
- `viewer.js`: `JOINT_NAMES` + `JOINT_TARGETS` rewritten to the G1's 29-joint
  actuator order (hip pitch/roll/yaw, knee, ankle pitch/roll ×2; waist
  yaw/roll/pitch; shoulder pitch/roll/yaw, elbow, wrist roll/pitch/yaw ×2);
  procedural rig rescaled to G1 proportions (~1.3 m); GLB attempt now points
  at `/assets/g1.glb` (absent → clean procedural fallback).
- `index.html` About panel + tests updated to G1 (29 joints, 67-dim).
  `test_env.py` and `test_ws.py` both pass.
- Model fetched via sparse clone into `mujoco_menagerie/unitree_g1/`
  (the menagerie submodule is uninitialized; this sits under the gitlink).

### Next
- Phase 8 — Manipulation Task System (8.1 first), now targeting G1.

---

## Session — Robot visual realism (Berkeley Humanoid Lite styling)
**Date**: 2026-06-07

### Robot visual realism — Berkeley Humanoid Lite styling
Restyled the procedural robot rig in `src/frontend/viewer.js` to resemble the
open-source Berkeley Humanoid Lite (a ~1 m, ~16 kg 3D-printed humanoid: light
white printed shells, dark structural joint housings, exposed cylindrical
actuator "pucks" at hips/shoulders/knees/elbows, blocky modular limb segments,
flat chest/pelvis panels, compact rectangular sensor head).

- **Color scheme / materials**: Replaced the single teal `MeshStandardMaterial`
  with a `robotMaterials()` factory returning three shared materials — an
  off-white printed `shell` (`0xeef0f2`, low metalness/high roughness), a dark
  metallic `joint` (`0x1b1d22`) for actuator housings, and a small teal
  `accent` (`0x00e5cc`, emissive) for a chest status strip. `ROBOT_TEAL` kept
  as the constant name (now the off-white shell color) plus new
  `ROBOT_JOINT_DARK` / `ROBOT_ACCENT` constants.
- **Geometry**: Switched limb shells from capsules to blocky rounded `BoxGeometry`
  shells (modular printed look). Torso is now a box chest shell; head is a
  compact rectangular box (was a sphere).
- **Detail meshes (cosmetic children inside pivots)**: Added `makeJointPuck()`
  helper producing dark cylinders; pucks sit at the shoulder, elbow, hip, and
  knee pivots. Torso pivot carries a dark pelvis girdle block, a dark shoulder
  yoke, and a teal emissive chest sensor strip. Head pivot carries a dark visor
  face. Hands and feet are dark joint-material blocks (gripper / sole).
- **Proportions**: Shrunk toward the ~0.9 m Berkeley Lite scale; legs still hang
  so feet reach ~y=0 at standing height.

### Animation contract preserved
- `makeSegment` keeps the pivot-at-joint convention (added an optional
  `details` array for cosmetic children at the pivot).
- `buildProceduralRobot()` still returns `{ root, segments }`; all 14 segment
  names intact: torso, head, {left,right}_{upper_arm,forearm,hand,thigh,shin,foot}.
- No changes to JOINT_NAMES, JOINT_TARGETS, applyJoints, installers, GLB/splat
  loaders, lobby, WS, waypoints, camera, or exports.
- Syntax verified: `node --input-type=module --check` passes.

---

## Session — Standing fix + splat alignment
**Date**: 2026-06-07

### Coordinate bug (robot looked sunk/sitting) — fixed
- Root cause: MuJoCo is **Z-up**, but `handleFrame` in `viewer.js` placed the
  robot with `position.set(x, y, z)` treating mj `y` (a ~0 horizontal coord)
  as the vertical, so the real pelvis height (mj `z`≈0.79) went onto a
  horizontal axis and the robot rendered sunk to the floor.
- Fix: remap mj `(x, y, z)` → three `(x, z, y)` so height lands on the Y axis
  (consistent with how obstacles/waypoints already map). Robot facing set to
  `π/2 − heading` (rig forward is +Z); follow-camera updated to trail along
  the travel direction.

### Untrained preview mode (no flailing) — added
- With no checkpoint the server was feeding random torques → the G1 fell
  instantly. Added `G1TraversalEnv.preview_step()`: a kinematic standing pose
  (held at the home keyframe) that glides the base toward the active waypoint
  at ~0.8 m/s and faces it — no dynamics, so it stays upright. `server.py`
  uses it when `model is None`; trained checkpoints still run real physics.
- Also added `home_pose_action()` (keyframe-pose action) for completeness.
- Verified: WS stream holds pelvis z=0.790 and advances toward the goal.

### Splat alignment wired
- `assets/scene.splat` created from `scene.ply` (5.72M splats, 183 MB) via the
  new `src/backend/ply_to_splat.py`. Server serves it (200 OK).
- `viewer.js` applies a `SPLAT_ALIGNMENT` transform on load with live console
  hooks (`window.splatTransform.setRotation/Position/Scale/get`) to tune
  against the real capture, then bake values back into the constant.

### Robot visual — Berkeley Humanoid Lite styling landed (parallel agent)
- See entry above; rig restyled to off-white shells + dark joint pucks. All 14
  segment names + animation contract preserved.

---

## Phase PF — Physical Fidelity & Sim-to-Real Validation (adapted to G1)
**Date**: 2026-06-07
**Note**: plan.md (`plan.md`) was written for the H1 robot. The live demo robot
is the Unitree G1 (29-DOF, `g1_env.py`). Per user decision, the whole PF phase
is **adapted to G1**: specs/files/joint-count/numbers all target G1, following
the plan's structure and intent. plan.md itself is NOT edited mid-run (run-plan
orchestrator rule); completion is tracked here.

### PF-0 — Spec config (`src/backend/g1_specs.py`) — COMPLETE
Single source of truth for real Unitree G1 numbers. Two honesty tiers:
- **MODEL (authoritative)**: peak torque per joint read from g1.xml
  `jnt_actfrcrange` (hip-roll/knee 139, hip-pitch/yaw + waist-yaw 88, ankle +
  waist-roll/pitch 50, arms 25, wrist-pitch/yaw 5 N·m); joint position ranges;
  29 actuators. `verify_against_model()` asserts the baked constants still match
  the loaded model so they cannot silently drift (passes).
- **PUBLISHED**: mass 35 kg (model sums ~33.3), height 1.32 m, 13S 9 Ah battery
  w/ 54 V charger → ~486 Wh, ~2 kg/arm payload (3 kg EDU), 29-DOF this variant.

### ASSUMPTIONS logged (not published by Unitree)
- **CONTINUOUS_TORQUE_NM = 0.35 × peak** — Unitree publishes no continuous
  (thermal) rating. Used only for the PF-3 *relative* duty-cycle warning.
- **VELOCITY_LIMIT_RAD_S = 30.0 (all joints)** — MuJoCo encodes no joint
  velocity limit and Unitree publishes no clean per-joint max speed. Conservative
  single default; relative saturation signal only.
- **BATTERY_WH = 486** — derived 9 Ah × 54 V (max/charge voltage); nominal
  (~47 V) would give ~423 Wh, so usable energy sits in ~423–486 Wh.
- **DEX_HAND_PAYLOAD_KG = 2.0** — dexterous-hand add-on; base G1 cannot grasp.

### Honesty note
Base G1 (and this 29-DOF model) has **no actuated fingers** → cannot grasp.
The model's `rubber_hand` geoms are fixed. PF-8 reframes manipulation as
push-based unless a task explicitly opts into an assumed dexterous hand.

### PF-1 — Actuator clamps + saturation logging — COMPLETE
- `src/backend/physical/saturation.py`: `SaturationLogger` — per joint per
  episode tracks peak |torque|, % of peak rating, near-limit "saturation event"
  steps (within 2% of limit), and the same for velocity. Validates inputs.
- `g1_env.py`: imports limits from `g1_specs` (no hardcoding). `__init__` calls
  `verify_against_model()`, drives MuJoCo `jnt_actfrcrange` from the spec
  (`_apply_force_limits`), and builds the logger. `step()` clamps position
  targets to ctrlrange (`_apply_control`) and records realised torque via
  `qfrc_actuator[6:6+n]` (post-clamp, so it respects the physics-enforced peak)
  plus joint velocity. `reset()` resets the logger.
- Old actuation kept as `_apply_control_old()` (don't delete working code).
- `get_saturation_report()` / `print_saturation_summary()`; auto-print at episode
  end only when `verbose_physical=True` (default False → no training spam).
- Test (`test_saturation.py`): random policy saturates all 29 joints to 100% of
  peak (expected — random position targets slam the kp=500 servos into the force
  limit), left_wrist_roll velocity flagged at 139% of the assumed limit. All
  joints stay within the physics-enforced peak. Original env smoke test still
  passes; server imports OK.
- Design note: G1 uses position actuators, so torque cannot be commanded
  directly; the realised joint torque is bounded by jnt_actfrcrange. We set that
  range from the spec so physics (not just Python) enforces the real limit.

### PF-2 — Power & energy budget — COMPLETE
- `src/backend/physical/power.py`: `PowerLogger`. Per step mechanical power per
  joint = torque * joint_vel; electrical draw P_elec = sum(max(p_joint,0)) / EFF
  (no regen recovery). Tracks peak electrical W, mean electrical W (energy/time),
  and est_runtime_min = BATTERY_WH / mean_W * 60.
- `g1_env.py`: `_log_physical()` now feeds both saturation (PF-1) and power
  (PF-2) loggers from the same realised torque/velocity; `get_power_report()`;
  reset + verbose print wired.
- **ASSUMPTION**: EFFICIENCY = 0.7 (Unitree does not publish drivetrain
  efficiency) — logged here.
- Test: random (worst-case) policy → mean ~7.2 kW → ~4 min runtime, peak ~22 kW.
  Matches plan expectation that a hard policy yields a *short* runtime; a trained
  gentle walker would land near the published ~2 h. est_runtime is finite/positive;
  peak >= mean >= 0.

### PF-3 — Thermal duty-cycle check — COMPLETE
- `src/backend/physical/thermal.py`: `ThermalLogger`. Sliding-window (default
  2 s = 1000 steps @ 500 Hz) RMS torque per joint via O(1) running sum-of-squares.
  Tracks per-joint max windowed RMS, % of continuous rating, overheat_risk bool,
  and over-duration (seconds windowed RMS stayed above continuous).
- `g1_env.py`: thermal logger wired into `_log_physical` / reset / verbose print;
  `get_thermal_report()` keyed by joint name.
- Output carries an explicit CAVEAT that continuous ratings are ASSUMPTIONS
  (0.35*peak), so overheat flags are a *relative* duty-cycle warning, not an
  absolute thermal prediction.
- Test: random policy flags 29/29 joints (RMS ~285.7% = 1/0.35 of continuous, as
  expected when peak torque is sustained). pct/duration non-negative, risk bool.

### PF-4 — Control-loop realism — COMPLETE
- `g1_env.py` gains an A/B realism path behind `realism_enabled` (+ `REALISM_CONFIG`
  block; all sigmas/latencies in one place). Ideal path untouched
  (`_physics_ideal`): one physics step per policy step, preserving the trained
  baseline and the A/B reference.
- Realistic path (`_physics_realistic`): policy rate decoupled from physics —
  POLICY_HZ=50 over 500 Hz physics = 10 substeps with zero-order hold; actuator
  latency 10 ms = 5-step ctrl buffer (apply oldest); obs latency 5 ms = 2-step
  proprio buffer; Gaussian sensor noise on joint pos/vel + IMU lin-vel + proj
  gravity. Goal vector is NOT noised/delayed (commanded target, not a sensor).
- Refactor: `step()` is now a dispatcher; reward/info extracted to
  `_post_physics`; obs split into `_proprio_vector` + `_goal_part`; `_observe`
  returns clean (ideal) or noisy+delayed (realistic). `reset` clears buffers and
  seeds the noise RNG from `seed` for reproducible A/B.
- **ASSUMPTIONS**: noise sigmas (joint_pos 0.01 rad, joint_vel 0.05 rad/s,
  lin_vel 0.05 m/s, proj_grav 0.02) and latencies — representative, not measured.
- Test (`test_realism.py`): same deterministic standing policy + seed survives
  158 steps ideal vs 16 steps with realism on (return 44.8 -> 4.2). That gap IS
  the sim-to-real risk. Ideal obs deterministic, realistic obs noisy (std ~0.05).
  Regression: test_env / test_saturation / server import all still pass.

### PF-5 — Contact/friction realism + domain randomization — COMPLETE
- **Floor added** (fidelity fix): the env loaded g1.xml (robot only, no ground),
  so under physics the robot free-fell and only stood via the kinematic
  preview_step. `_build_model()` now uses MjSpec to add a ground plane (asset
  paths preserved, unlike an out-of-dir <include>) with tuned solref
  (0.02,1) / solimp (0.9,0.95,0.001,0.5,2) to avoid sink/jitter. The robot can
  now actually stand on physics (home pose survives 400 steps).
- `CONTACT_CONFIG`: foot-floor friction 0.6 (foot geoms, priority=1 → dominates
  foot-floor contact), object-floor friction 0.5 (floor's value, governs object
  contacts), hand-object friction 0.8 (for PF-8 objects). Foot geoms found by
  ankle_roll body membership.
- `domain_randomization()` (off by default; `domain_rand_enabled`): per-episode
  samples foot slide friction (applied to foot geoms), object mass, payload
  offset; applies mass to `object`/`payload` bodies when present (PF-8) and
  records `_dr_state`. Called from `reset()` when enabled.
- Test (`test_domain_rand.py`): 5 episodes, foot friction varies 0.41-0.93 and
  object mass varies, obs stays finite (no exploding contacts), off by default.
- Side effect: PF-4 realism A/B gap on the *standing* home policy shrank (158-vs-16
  steps was a no-floor artifact; now both stand 400 steps with a small ~0.07
  return gap). Realism mechanism still verified directly (noisy obs std ~0.05).

### PF-6 — Stability & payload feasibility — COMPLETE
- `src/backend/physical/stability.py`: pure-numpy `convex_hull` (monotone chain)
  + `support_margin` (signed distance to polygon, +inside/-outside), and
  `StabilityLogger`.
- `g1_env.py`: per physics step computes whole-robot CoM (`_com_xy`, mass-weighted
  from xipos) and the support polygon (`_support_hull`, convex hull of active
  floor-contact points), feeding `update_stability`. `get_stability_report()`;
  reset + verbose print wired.
- Tipping: flags steps where CoM ground projection leaves the support polygon;
  reports tipping_violations and min_support_margin_m.
- Payload: `update_payload(mass, arm_extension)` computes shoulder static moment
  (mass*g*ext) vs G1 arm peak (25 N·m), flags >60% (dynamics headroom) and mass
  over CONTINUOUS_PAYLOAD_KG (2-3 kg/arm). Called by carry tasks (PF-8); exercised
  directly in the test for now.
- Test (`test_stability.py`): geometry (centre +0.5 / outside -1.0), live standing
  robot 0 tipping with CoM ~5 cm inside support polygon, payload 2kg@0.30m OK
  (23.5%) vs 5kg@0.40m infeasible (78.5%, over cap). All PF-1..5 regressions pass.
