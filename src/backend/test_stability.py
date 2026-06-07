"""PF-6 smoke test: tipping/support margin + payload feasibility."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from src.backend.g1_env import G1TraversalEnv
from src.backend.physical.stability import convex_hull, support_margin, StabilityLogger
from src.backend import g1_specs

# --- geometry sanity ---
square = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
hull = convex_hull(square)
assert len(hull) == 4
assert support_margin(np.array([0.5, 0.5]), hull) > 0, "centre must be inside"
assert support_margin(np.array([2.0, 0.5]), hull) < 0, "outside point must be negative"
print(f"geometry OK: centre margin {support_margin(np.array([0.5,0.5]),hull):+.3f}, "
      f"outside margin {support_margin(np.array([2.0,0.5]),hull):+.3f}")

# --- live tipping check on the standing robot ---
env = G1TraversalEnv()
env.reset(seed=0)
for _ in range(120):
    obs, r, term, trunc, _ = env.step(env.home_pose_action())
    if term or trunc:
        break
stab = env.get_stability_report()
assert "tipping_violations" in stab and "min_support_margin_m" in stab
assert stab["min_support_margin_m"] is not None
print(env._stability_logger.summary_str())
# Standing on two feet: CoM should sit inside the support polygon most of the time.
print(f"standing: tipping {stab['tipping_violations']} steps, "
      f"min margin {stab['min_support_margin_m']:+.3f} m")

# --- payload feasibility logic (no carry task yet -> exercise directly) ---
arm_peak = g1_specs.PEAK_TORQUE_NM['left_shoulder_pitch_joint']  # 25 N·m
log = StabilityLogger(arm_peak, g1_specs.CONTINUOUS_PAYLOAD_KG)
# 2 kg at 0.30 m extension: moment = 2*9.81*0.30 = 5.89 N·m = 23.5% of 25 -> OK
log.update_payload(2.0, 0.30)
r_ok = log.report()
assert r_ok["payload_ok"] is True
assert 20 < r_ok["shoulder_moment_pct_of_limit"] < 30

# 5 kg at 0.40 m: over the 60% torque threshold AND over the 3 kg payload cap
log2 = StabilityLogger(arm_peak, g1_specs.CONTINUOUS_PAYLOAD_KG)
log2.update_payload(5.0, 0.40)
r_bad = log2.report()
assert r_bad["payload_ok"] is False
print(f"payload: 2kg@0.30m -> {r_ok['shoulder_moment_pct_of_limit']:.1f}% ok={r_ok['payload_ok']}; "
      f"5kg@0.40m -> {r_bad['shoulder_moment_pct_of_limit']:.1f}% ok={r_bad['payload_ok']}")
print("PASS — support polygon/margin, live tipping check, and payload feasibility all work")
