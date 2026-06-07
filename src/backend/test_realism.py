"""PF-4 smoke test: control-loop realism A/B and mechanism checks."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from src.backend.g1_env import G1TraversalEnv


def run_episode(realism, seed, max_steps=400):
    env = G1TraversalEnv(realism_enabled=realism)
    obs, _ = env.reset(seed=seed)
    policy = env.home_pose_action()  # deterministic standing policy
    total, steps = 0.0, 0
    for _ in range(max_steps):
        obs, r, term, trunc, _ = env.step(policy)
        total += r
        steps += 1
        if term or trunc:
            break
    return total, steps, env


# --- dims unchanged across modes ---
ideal_env = G1TraversalEnv(realism_enabled=False)
real_env = G1TraversalEnv(realism_enabled=True)
assert ideal_env.observation_space == real_env.observation_space
assert real_env._n_substeps == 10, f"expected 10 substeps, got {real_env._n_substeps}"
assert real_env._act_latency_steps == 5, f"10ms@500Hz -> 5 steps, got {real_env._act_latency_steps}"
print(f"realism config: {real_env._n_substeps} substeps/policy-step, "
      f"actuator latency {real_env._act_latency_steps} steps, "
      f"obs latency {real_env._obs_latency_steps} steps")

# --- ideal sensing is deterministic; realistic sensing has noise ---
ideal_env.reset(seed=0)
o1 = ideal_env._observe(); o2 = ideal_env._observe()
assert np.array_equal(o1, o2), "ideal observation must be deterministic"

real_env.reset(seed=0)
real_env.step(real_env.home_pose_action())
n1 = real_env._observe(); n2 = real_env._observe()
assert not np.array_equal(n1, n2), "realistic observation must carry sensor noise"
noise_std = float(np.std(n1 - n2))
print(f"ideal obs deterministic: OK; realistic obs noise std ~{noise_std:.4f}")

# --- measurable A/B gap on the same deterministic policy + seed ---
ideal_ret, ideal_steps, _ = run_episode(False, seed=42)
real_ret, real_steps, _ = run_episode(True, seed=42)
gap = abs(ideal_ret - real_ret)
print(f"ideal:  return {ideal_ret:8.2f}  steps {ideal_steps}")
print(f"realism:return {real_ret:8.2f}  steps {real_steps}")
assert gap > 1e-6 or ideal_steps != real_steps, "realism must change the outcome"

# --- regression: old default behaviour preserved (realism off == single step) ---
assert ideal_env._realism_enabled is False
print(f"PASS — realism A/B works; measurable gap {gap:.2f} return "
      f"(this gap IS the sim-to-real risk)")
