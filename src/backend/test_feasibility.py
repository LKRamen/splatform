"""PF-7 test: aggregate verdict, env integration, JSON persistence."""
import sys, os, json, tempfile, glob
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from src.backend.g1_env import G1TraversalEnv
from src.backend.physical import feasibility as feas

# --- verdict rules ---
# clean sections -> FEASIBLE
ok = feas.build_feasibility_report(
    saturation={'j': {'peak_torque_pct': 40.0, 'torque_saturation_frac': 0.0}},
    power={'est_runtime_min': 120.0},
    thermal={'j': {'overheat_risk': False, 'over_duration_s': 0.0}},
    stability={'tipping_violations': 0, 'tipping_violation_frac': 0.0, 'payload_ok': True},
)
assert ok['verdict'] == feas.FEASIBLE, ok

# a joint pinned at peak >20% of steps -> INFEASIBLE
bad = feas.build_feasibility_report(
    saturation={'knee': {'peak_torque_pct': 100.0, 'torque_saturation_frac': 0.5}},
)
assert bad['verdict'] == feas.INFEASIBLE and bad['worst_joint'] == 'knee', bad

# payload over limit -> INFEASIBLE; brief thermal -> MARGINAL
assert feas.build_feasibility_report(
    stability={'tipping_violations': 0, 'tipping_violation_frac': 0.0, 'payload_ok': False}
)['verdict'] == feas.INFEASIBLE
assert feas.build_feasibility_report(
    thermal={'j': {'overheat_risk': True, 'over_duration_s': 0.3}}
)['verdict'] == feas.MARGINAL
# no data -> N/A
assert feas.build_feasibility_report()['verdict'] == feas.NA
print("verdict rules OK (FEASIBLE / INFEASIBLE / MARGINAL / N/A)")

# --- env aggregation: physics run yields a real verdict ---
env = G1TraversalEnv()
env.reset(seed=0)
for _ in range(150):
    obs, r, term, trunc, _ = env.step(env.action_space.sample())  # random -> stressed
    if term or trunc:
        break
report = env.get_feasibility_report()
assert report['verdict'] in (feas.FEASIBLE, feas.MARGINAL, feas.INFEASIBLE)
assert report['sections']['saturation'] is not None
print(f"physics run verdict: {report['verdict']} — {report['reason']} "
      f"(worst joint {report['worst_joint']})")

# --- preview mode: stability-only verdict (no torque data) ---
env2 = G1TraversalEnv()
env2.reset(seed=0)
for _ in range(30):
    env2.preview_step()
prev = env2.get_feasibility_report()
assert prev['sections']['saturation'] is None, "preview has no torque sections"
assert prev['sections']['stability'] is not None, "preview still has stability"
assert prev['verdict'] != feas.NA, "preview should yield a stability-based verdict"
print(f"preview verdict (stability-only): {prev['verdict']} — {prev['reason']}")

# --- compact payload shape for the WS frame ---
c = feas.compact(report)
assert set(c) == {'verdict', 'reason', 'worst_joint'}

# --- JSON persistence ---
with tempfile.TemporaryDirectory() as d:
    path = feas.save_feasibility_report(report, d, 'v_test')
    assert os.path.exists(path)
    saved = json.load(open(path))
    assert saved['verdict'] == report['verdict']
    assert path.endswith('.json') and 'feasibility' in path
print(f"PASS — feasibility verdict, env aggregation, preview fallback, "
      f"compact frame payload, and JSON persistence all work")
