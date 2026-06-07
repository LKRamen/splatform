# Fordham Lincoln Center — Robot Trainer

A hackathon demo that places a real **Unitree G1** humanoid robot (MuJoCo physics)
inside a Gaussian splat reconstruction of Fordham Lincoln Center. Select a PPO
policy checkpoint, set waypoints, and watch the robot navigate the real space.
When no splat or checkpoint is present it falls back gracefully (procedural
indoor lobby + a standing/glide preview), so a fresh clone runs out of the box.

## Requirements

- Python 3.11+ (tested on 3.13)
- Node 18+ (only for the optional GLB rebuild)

## Install

```bash
pip install mujoco gymnasium stable-baselines3 fastapi uvicorn websockets numpy
```

### Fetch the robot model (required)

The MuJoCo Menagerie is referenced as a submodule but only the model used at
runtime needs to be present. A sparse checkout keeps the download small:

```bash
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/google-deepmind/mujoco_menagerie.git .tmp_menagerie
git -C .tmp_menagerie sparse-checkout set unitree_g1
cp -r .tmp_menagerie/unitree_g1 mujoco_menagerie/unitree_g1
rm -rf .tmp_menagerie
```

The server loads `mujoco_menagerie/unitree_g1/g1.xml` (29-DOF G1). The retired
H1 env (`src/backend/h1_env.py`) expects `unitree_h1/h1.xml` if you ever switch
back.

## Start Server

```bash
python -m uvicorn src.backend.server:app --port 8765
```

Then open `http://localhost:8765`. With no checkpoints present the robot runs a
kinematic **standing/glide preview** toward the waypoints (no flailing); once
you train policies it runs the learned PPO controller under full physics.

## Run Training (overnight)

```bash
python src/backend/train.py
```

Saves checkpoints to `src/backend/checkpoints/v1.zip` (10k steps),
`v2.zip` (30k), `v3.zip` (60k).

## Add the Fordham Splat

The splat assets are **not** committed (large binaries, see `.gitignore`).
Drop your capture in as `scene.ply` at the repo root and convert it:

```bash
python -m src.backend.ply_to_splat scene.ply assets/scene.splat
```

The viewer auto-loads `assets/scene.splat` (showing a "Loading… X%" overlay)
and replaces the procedural lobby on success; otherwise the lobby stays.

### Aligning the splat

Reconstructions rarely arrive in the viewer's Y-up frame. Tune alignment live
from the browser console, then bake the values into `SPLAT_ALIGNMENT` in
`src/frontend/viewer.js`:

```js
splatTransform.setRotation(-90, 0, 0)   // XYZ Euler degrees
splatTransform.setScale(1.5)
splatTransform.setPosition(0, -1.2, 0)
splatTransform.get()                    // read current values to bake in
```

## API

| Route | Method | Description |
|---|---|---|
| `/health` | GET | Server status + available checkpoints |
| `/checkpoints` | GET | List checkpoint files |
| `/waypoints` | POST | Set navigation targets `{"waypoints": [[x,z], ...]}` |
| `/simulate/{v}` | WS | Stream 29 joint angles + position + scores at 50 fps |

## Observation / action contract

`G1TraversalEnv` derives its dimensions from the model: **67-dim** observation
(29 joint_pos + 29 joint_vel + 3 base lin_vel + 3 projected_gravity +
2 goal_vector + 1 goal_dist), **29-dim** action. The WS frame sends `joints`
as 29 floats in MuJoCo G1 actuator order (see `CLAUDE.md`).
