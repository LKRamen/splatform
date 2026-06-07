"""
FastAPI WebSocket server for H1 traversal simulator.
Usage: python -m uvicorn src.backend.server:app --port 8765
"""
import os, sys, asyncio, glob, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from stable_baselines3 import PPO
from src.backend.h1_env import H1TraversalEnv

CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), 'checkpoints')
FRAME_INTERVAL = 0.02   # 50 fps

_frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend'))
_assets_dir   = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../assets'))

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

# ------------------------------------------------------------------
# API routes — must be registered BEFORE the catch-all static mount
# ------------------------------------------------------------------
_current_waypoints: list[list[float]] = [[5.0, 0.0]]


def _list_checkpoints():
    return sorted([
        os.path.basename(f).replace('.zip', '')
        for f in glob.glob(os.path.join(CHECKPOINT_DIR, 'v*.zip'))
    ])


@app.get('/health')
def health():
    return {'status': 'ok', 'checkpoints': _list_checkpoints()}


@app.get('/checkpoints')
def checkpoints():
    return {'checkpoints': [
        {'name': os.path.basename(f).replace('.zip', ''), 'path': f}
        for f in sorted(glob.glob(os.path.join(CHECKPOINT_DIR, 'v*.zip')))
    ]}


class WaypointsBody(BaseModel):
    waypoints: list[list[float]]


@app.post('/waypoints')
def set_waypoints(body: WaypointsBody):
    global _current_waypoints
    _current_waypoints = body.waypoints
    return {'status': 'ok', 'count': len(_current_waypoints)}


@app.websocket('/simulate/{checkpoint_version}')
async def simulate(websocket: WebSocket, checkpoint_version: str):
    await websocket.accept()
    ckpt_path = os.path.join(CHECKPOINT_DIR, f'{checkpoint_version}.zip')
    env = H1TraversalEnv(waypoints=[np.array(wp) for wp in _current_waypoints])
    model = None
    if os.path.exists(ckpt_path):
        model = PPO.load(ckpt_path, env=env)
    obs, _ = env.reset()
    try:
        while True:
            if model is not None:
                action, _ = model.predict(obs, deterministic=True)
            else:
                action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            frame = {
                'joints':    env.data.qpos[7:26].tolist(),
                'position':  info['position'],
                'heading':   info['heading'],
                'step':      env._step_count,
                'scores':    info['scores'],
                'obstacles': info.get('obstacles', []),
            }
            await websocket.send_text(json.dumps(frame))
            if terminated or truncated:
                obs, _ = env.reset()
            await asyncio.sleep(FRAME_INTERVAL)
    except WebSocketDisconnect:
        pass


# ------------------------------------------------------------------
# Static file serving — AFTER all API routes
# ------------------------------------------------------------------
@app.get('/')
def index():
    return FileResponse(os.path.join(_frontend_dir, 'index.html'))


@app.get('/compare')
def compare():
    return FileResponse(os.path.join(_frontend_dir, 'compare.html'))


@app.get('/capture')
def capture():
    return FileResponse(os.path.join(_frontend_dir, 'capture.html'))


if os.path.isdir(_assets_dir):
    app.mount('/assets', StaticFiles(directory=_assets_dir), name='assets')

# Serve frontend JS/CSS files — mount LAST so it doesn't shadow API routes
if os.path.isdir(_frontend_dir):
    app.mount('/ui', StaticFiles(directory=_frontend_dir), name='ui')
