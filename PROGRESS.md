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

### Next
- 7.B (indoor lobby fallback) and 7.C (splat pipeline + indicator).
