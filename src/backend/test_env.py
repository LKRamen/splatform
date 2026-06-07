import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from src.backend.h1_env import H1TraversalEnv

env = H1TraversalEnv()
obs, _ = env.reset()
assert obs.shape == (47,), f'Expected (47,), got {obs.shape}'

rewards = []
for i in range(200):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    rewards.append(reward)
    if terminated or truncated:
        obs, _ = env.reset()

mean_r = float(np.mean(rewards))
print(f'PASS — 200 steps completed, mean reward: {mean_r:.4f}')
print(f'Sample obs[:5]: {obs[:5]}')
print(f'Sample scores: {info["scores"]}')
