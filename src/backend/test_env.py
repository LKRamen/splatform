import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from src.backend.g1_env import G1TraversalEnv

env = G1TraversalEnv()
obs, _ = env.reset()
expected = env.observation_space.shape
assert obs.shape == expected, f'Expected {expected}, got {obs.shape}'
assert env.n_joints == 29, f'Expected 29 G1 joints, got {env.n_joints}'

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
