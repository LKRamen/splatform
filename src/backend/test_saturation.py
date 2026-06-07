"""PF-1 smoke test: one episode, confirm saturation report prints & flags."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from src.backend.g1_env import G1TraversalEnv
from src.backend.g1_specs import JOINT_NAMES

env = G1TraversalEnv(verbose_physical=False)
obs, _ = env.reset()

# Drive with random actions to provoke high torques/velocities.
for _ in range(300):
    obs, r, term, trunc, info = env.step(env.action_space.sample())
    if term or trunc:
        break

report = env.get_saturation_report()
assert len(report) == env.n_joints, "report must cover every joint"
for name, r in report.items():
    assert r["peak_torque_pct"] <= 100.0 + 1e-6, f"{name} torque over 100% of peak"
    assert r["torque_saturation_steps"] >= 0
    assert 0.0 <= r["torque_saturation_frac"] <= 1.0

print(env._sat_logger.summary_str())
worst_name, worst_pct = env._sat_logger.worst_joint()
print(f"\nworst joint: {worst_name} at {worst_pct:.1f}% of peak torque")

# PF-2: power & energy budget
power = env.get_power_report()
import math
assert power["peak_power_w"] >= power["mean_power_w"] >= 0.0
assert power["mean_power_w"] > 0.0, "random thrashing should draw power"
assert math.isfinite(power["est_runtime_min"]) and power["est_runtime_min"] > 0.0
print("\n" + env._power_logger.summary_str())

# PF-3: thermal duty cycle
thermal = env.get_thermal_report()
assert len(thermal) == env.n_joints
for name, r in thermal.items():
    assert r["pct_of_continuous"] >= 0.0
    assert isinstance(r["overheat_risk"], bool)
    assert r["over_duration_s"] >= 0.0
n_risk = sum(1 for r in thermal.values() if r["overheat_risk"])
print("\n" + env._thermal_logger.summary_str(JOINT_NAMES))
print(f"PASS — saturation {len(report)} joints; runtime {power['est_runtime_min']:.1f} min; "
      f"thermal flagged {n_risk}/{env.n_joints} joints over (assumed) continuous rating")
