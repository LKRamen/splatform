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

### Next
- Phase 8 — Manipulation Task System (8.1 first).
