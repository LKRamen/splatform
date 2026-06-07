# Fordham Lincoln Center — Robot Manipulation Trainer

## What this project is
A hackathon demo that places a real Unitree G1 humanoid robot (driven by
MuJoCo physics) inside a photorealistic Gaussian splat reconstruction of
Fordham Lincoln Center. The robot learns to perform real-world manipulation
tasks — moving boxes, setting up tables, sorting objects — the same class
of tasks Amazon, Figure, and 1X are training humanoid robots for in
warehouses and offices. Users select a task, watch the robot attempt it
across training checkpoints, and see measurable improvement.

## Read these files before every session
- `GOALS.md` — ordered task list, pick up from the first incomplete item
- `PROGRESS.md` — what has been built, what failed, what decisions were made

## Stack
- **Backend**: Python 3.11, FastAPI, uvicorn, websockets
- **Physics**: `mujoco` (pip), MuJoCo Menagerie `unitree_g1/g1.xml` (29 DOF)
- **Training**: `stable-baselines3`, `gymnasium`, custom `G1TraversalEnv`
  (`src/backend/g1_env.py`; the older H1 env is retained in `h1_env.py`)
- **Frontend**: Vanilla JS + Three.js r158, `@mkkellogg/gaussian-splats-3d`
- **Splat source**: PostShot or Luma AI — exports `.ply` / `.splat`
- **Robot mesh**: Procedural Three.js rig (capsules/boxes) matching G1
  proportions, falls back from GLB if skeleton invalid

## File structure
```
fordham-traversal/
├── CLAUDE.md
├── GOALS.md
├── PROGRESS.md
├── src/
│   ├── backend/
│   │   ├── server.py
│   │   ├── h1_env.py          ← base env, now extended by task envs
│   │   ├── tasks/
│   │   │   ├── box_sort.py    ← push colored boxes to matching zones
│   │   │   ├── table_setup.py ← move chairs/objects to target positions
│   │   │   ├── package_delivery.py ← carry box from A to B
│   │   │   └── obstacle_course.py  ← step over/around barriers
│   │   ├── train.py
│   │   └── checkpoints/
│   ├── frontend/
│   │   ├── index.html
│   │   ├── viewer.js          ← Three.js scene + robot + object rendering
│   │   ├── controls.js
│   │   ├── scoring.js
│   │   └── tasks.js           ← task selector UI, object state rendering
│   └── training/
│       └── rewards.py
└── assets/
    ├── h1.glb
    └── scene.splat
```

## Behavior rules
- **Always update PROGRESS.md** at end of every work block.
- **Never delete working code.** Move to `_old` suffix first.
- **Commit after each completed goal item.** Format: `feat: <description>`
- **If blocked**, log clearly in PROGRESS.md and move to next item.
- **Do not gold-plate.** Simplest thing that satisfies the goal, then move on.
- **Splat fallback**: always render a procedural indoor lobby (walls, ceiling,
  columns, interior lighting) when `assets/scene.splat` is missing. Never
  a blank void.
- **Robot fallback**: always render a clean procedural capsule+box rig when
  `assets/h1.glb` is missing or has no valid skeleton.

## WebSocket contract
Server sends JSON every 20ms:
```json
{
  "joints": [29 floats],
  "position": [x, y, z],
  "heading": float,
  "step": int,
  "task": "box_sort",
  "objects": [
    {"id": "box_red", "pos": [x,y,z], "rot": [x,y,z,w], "type": "box"},
    {"id": "box_blue", "pos": [x,y,z], "rot": [x,y,z,w], "type": "box"},
    {"id": "zone_red", "pos": [x,y,z], "type": "zone"},
    {"id": "zone_blue", "pos": [x,y,z], "type": "zone"}
  ],
  "scores": {
    "task_completion": float,
    "manipulation_precision": float,
    "gait_stability": float,
    "energy": float,
    "total": float
  },
  "feasibility": {
    "verdict": "FEASIBLE | MARGINAL | INFEASIBLE | N/A",
    "reason": "one-line explanation of the dominant limit",
    "worst_joint": "joint name most stressed, or null"
  }
}
```

The `feasibility` field (PF-7) is the live hardware-feasibility verdict
aggregating the physical-fidelity checks (actuator saturation, power/runtime,
thermal duty cycle, stability/payload). `N/A` is sent in kinematic preview mode
(no trained checkpoint → no actuator torques); a real (physics) run yields
FEASIBLE/MARGINAL/INFEASIBLE. Full per-run reports are saved as JSON under
`src/backend/checkpoints/<ckpt>/feasibility/`.

## Observation space
**Implemented now — `G1TraversalEnv` (67-dim):** joint_pos (29) + joint_vel
(29) + base_lin_vel (3) + projected_gravity (3) + goal_vector (2) +
goal_dist (1). Dimensions are derived from the model (`model.nu`), so they
track the robot automatically.

**Planned — `G1ManipulationEnv` (manipulation target, not yet built):**
base_height (1), base_lin_vel (3), base_ang_vel (3), projected_gravity (3),
joint_pos (29), joint_vel (29), right_hand_pos (3), left_hand_pos (3),
object_pos (3), object_vel (3), object_to_target (3), task_phase (1).

## Scoring rubric
| Dimension        | Weight | Signal                              |
|------------------|--------|-------------------------------------|
| Task completion  | 35%    | object reached target zone          |
| Manip. precision | 25%    | object deviation from ideal path    |
| Gait stability   | 20%    | torso height variance + ang. dev.   |
| Energy           | 20%    | -sum(torques²) per step             |

## Real-world framing (for demo narrative)
This is the same problem Amazon Sequoia, Figure 02, and Unitree G1 are
solving: training humanoid robots to perform useful physical tasks in
real spaces. Our system does this in a digital twin of the actual venue,
trained overnight with PPO, showing measurable checkpoint improvement.
