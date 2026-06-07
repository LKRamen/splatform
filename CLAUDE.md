# Fordham Lincoln Center — Robot Traversal Trainer

## What this project is
A hackathon project that places a real Unitree H1 humanoid robot (driven by MuJoCo physics) inside a photorealistic Gaussian splat reconstruction of Fordham Lincoln Center. Users select a traversal model checkpoint, set waypoints, and watch the robot navigate the real space. The system trains PPO policies overnight and shows measurable improvement across checkpoints.

## Read these files before every session
- `GOALS.md` — ordered task list, pick up from the first incomplete item
- `PROGRESS.md` — what has been built, what failed, what decisions were made

## Stack
- **Backend**: Python 3.11, FastAPI, uvicorn, websockets
- **Physics**: `mujoco` (pip), MuJoCo Menagerie `unitree_h1/h1.xml`
- **Training**: `stable-baselines3`, `gymnasium`, custom `H1TraversalEnv`
- **Frontend**: Vanilla JS + Three.js r158, `@mkkellogg/gaussian-splats-3d`, `urdf-loader`
- **Splat source**: PostShot (local) or Luma AI free tier — exports `.ply` / `.splat`
- **Robot mesh**: Unitree H1 OBJ meshes from Menagerie → converted to GLB via `obj2gltf`

## File structure
```
fordham-traversal/
├── CLAUDE.md          ← this file
├── GOALS.md           ← ordered task list
├── PROGRESS.md        ← session log
├── src/
│   ├── backend/
│   │   ├── server.py          ← FastAPI WebSocket server
│   │   ├── h1_env.py          ← Custom Gymnasium env for H1
│   │   ├── train.py           ← PPO training script
│   │   └── checkpoints/       ← saved .zip policy files
│   ├── frontend/
│   │   ├── index.html         ← main app shell
│   │   ├── viewer.js          ← Three.js splat + robot scene
│   │   ├── controls.js        ← waypoint UI, checkpoint selector
│   │   └── scoring.js         ← live score display
│   └── training/
│       └── rewards.py         ← reward functions (imported by h1_env.py)
└── assets/
    ├── h1.glb                 ← converted Unitree H1 mesh
    └── scene.splat            ← Fordham splat file (add after capture)
```

## Behavior rules
- **Always update PROGRESS.md** at the end of every work block. Log what was completed, what broke, what was decided, and what the next session should start with.
- **Never delete working code.** If something needs replacing, move it to a `_old` suffix first.
- **Commit after each completed goal item.** Message format: `feat: <goal item description>`.
- **If a goal is blocked**, write the blocker clearly in PROGRESS.md under "Blockers" and move to the next unblocked goal.
- **Do not gold-plate.** Build the simplest thing that satisfies each goal item, then move on.
- **The splat file will not exist until morning.** Build everything so it gracefully falls back to a procedural NYC-style test scene when `assets/scene.splat` is missing.

## Key technical contracts
- The WebSocket server sends JSON: `{"joints": [19 floats], "position": [x,y,z], "heading": float, "step": int, "score": {...}}`
- Joint order matches MuJoCo Menagerie H1 actuator order exactly (left_hip_yaw, left_hip_roll, left_hip_pitch, left_knee, left_ankle, right_hip_yaw, right_hip_roll, right_hip_pitch, right_knee, right_ankle, torso, left_shoulder_pitch, left_shoulder_roll, left_elbow, right_shoulder_pitch, right_shoulder_roll, right_elbow, left_wrist_roll, right_wrist_roll)
- The frontend connects to `ws://localhost:8765` and drives the URDF/GLB joint angles from incoming data
- Checkpoints are saved to `src/backend/checkpoints/v1.zip`, `v2.zip`, `v3.zip`

## H1TraversalEnv observation space (47-dim)
- base_height (1), base_lin_vel (3), base_ang_vel (3), projected_gravity (3)
- joint_pos (19), joint_vel (19)
- goal_vector (2), goal_dist (1), prev_action (19) — wait, that's 70... trim to: joint_pos (19) + joint_vel (19) + base_lin_vel (3) + projected_gravity (3) + goal_vector (2) + goal_dist (1) = 47

## Scoring rubric (used in both env reward and frontend display)
| Dimension | Weight | Signal |
|---|---|---|
| Waypoint efficiency | 30% | progress toward goal / steps taken |
| Gait stability | 25% | torso height variance + angular deviation |
| Obstacle clearance | 20% | min distance to collision geometry |
| Energy expenditure | 15% | -sum(torques²) per step |
| Completion rate | 10% | reached all waypoints without falling |
