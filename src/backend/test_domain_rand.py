"""PF-5 smoke test: contact friction + domain randomization across episodes."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from src.backend.g1_env import G1TraversalEnv

# --- floor exists with tuned contact params ---
env = G1TraversalEnv(domain_rand_enabled=True)
import mujoco as mj
floor_id = mj.mj_name2id(env.model, mj.mjtObj.mjOBJ_GEOM, 'floor')
assert floor_id != -1, "PF-5 must add a ground plane"
assert len(env._foot_geom_ids) == 8, f"expected 8 foot geoms, got {len(env._foot_geom_ids)}"
print(f"floor geom id {floor_id}; {len(env._foot_geom_ids)} foot contact geoms")

# --- friction & mass vary per episode, sim stays stable ---
frictions, masses = [], []
for ep in range(5):
    env.reset(seed=ep)
    frictions.append(env._dr_state['foot_friction'])
    masses.append(env._dr_state['object_mass'])
    # confirm sampled friction was actually written to the foot geoms
    applied = env.model.geom_friction[env._foot_geom_ids[0]][0]
    assert abs(applied - env._dr_state['foot_friction']) < 1e-9
    lo, hi = env._dr['foot_friction_range']
    assert lo <= applied <= hi
    for _ in range(80):
        obs, r, term, trunc, _ = env.step(env.home_pose_action())
        assert np.all(np.isfinite(obs)), f"ep {ep}: non-finite obs (contact blew up)"
        if term or trunc:
            break

print("per-episode foot friction:", [round(f, 3) for f in frictions])
assert len(set(round(f, 4) for f in frictions)) > 1, "friction must vary across episodes"
assert len(set(round(m, 4) for m in masses)) > 1, "object mass must vary across episodes"

# --- randomization off by default ---
env_off = G1TraversalEnv()
assert env_off._domain_rand_enabled is False
mu0 = env_off.model.geom_friction[env_off._foot_geom_ids[0]][0]
assert abs(mu0 - 0.6) < 1e-9, "default foot friction should be the config 0.6"

print(f"PASS — domain randomization varies friction {min(frictions):.2f}-{max(frictions):.2f} "
      f"and object mass across 5 episodes; sim stayed finite/stable; off by default")
