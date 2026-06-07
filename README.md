# Fordham Lincoln Center — Robot Traversal Trainer

A hackathon demo that places a real Unitree H1 humanoid robot (MuJoCo physics) inside a Gaussian splat reconstruction of Fordham Lincoln Center. Select a PPO policy checkpoint, set waypoints, and watch the robot navigate the real space.

## Requirements

- Python 3.11+
- Node 18+ (only for GLB asset rebuild if needed)

## Install

```bash
pip install mujoco stable-baselines3 gymnasium fastapi uvicorn websockets numpy aiofiles trimesh
git clone https://github.com/google-deepmind/mujoco_menagerie.git
```

## Run Training (overnight)

```bash
python src/backend/train.py
```

Saves checkpoints to `src/backend/checkpoints/v1.zip` (10k steps), `v2.zip` (30k steps), `v3.zip` (60k steps).

## Start Server

```bash
python -m uvicorn src.backend.server:app --port 8765
```

Then open `http://localhost:8765` in your browser.

## Build Robot GLB (optional — already included)

```bash
python src/backend/build_glb.py
```

Merges 21 Unitree H1 STL meshes into `assets/h1.glb`.

## Add Fordham Splat (morning of demo)

Copy your captured splat file to `assets/scene.splat`. The viewer will automatically load it instead of the procedural NYC scene.

## API

| Route | Method | Description |
|---|---|---|
| `/health` | GET | Server status + available checkpoints |
| `/checkpoints` | GET | List checkpoint files |
| `/waypoints` | POST | Set navigation targets `{"waypoints": [[x,z], ...]}` |
| `/simulate/{v}` | WS | Stream joint angles + scores at 50fps |
