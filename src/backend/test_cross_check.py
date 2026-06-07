"""PF-9 test: feasibility tooling generalizes to a second robot profile."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from src.backend import g1_specs, berkeley_lite_specs as bk
from src.backend.physical.saturation import SaturationLogger
from src.backend.physical import feasibility as feas

# --- both profiles expose the same interface ---
for spec in (g1_specs, bk):
    assert len(spec.JOINT_NAMES) == spec.NUM_DOF
    assert spec.peak_torque_array().shape == (spec.NUM_DOF,)
    assert spec.continuous_torque_array().shape == (spec.NUM_DOF,)
    assert spec.velocity_limit_array().shape == (spec.NUM_DOF,)
    assert spec.BATTERY_WH > 0 and spec.MASS_KG > 0
print(f"G1: {g1_specs.NUM_DOF} DOF, {g1_specs.MASS_KG} kg, {g1_specs.BATTERY_WH} Wh")
print(f"Berkeley Lite: {bk.NUM_DOF} DOF, {bk.MASS_KG} kg, {bk.BATTERY_WH} Wh")

# --- the SAME SaturationLogger works on the Berkeley profile ---
log = SaturationLogger(list(bk.JOINT_NAMES), bk.peak_torque_array(), bk.velocity_limit_array())
peak = bk.peak_torque_array()
# half-peak torques on every joint -> ~50% usage, no saturation
log.update(0.5 * peak, np.zeros(bk.NUM_DOF))
rep = log.report()
assert len(rep) == bk.NUM_DOF
some = next(iter(rep.values()))
assert 49.0 < some["peak_torque_pct"] < 51.0, some

# --- the SAME feasibility engine produces a verdict from Berkeley sections ---
bk_sat = {n: {"peak_torque_pct": 100.0, "torque_saturation_frac": 0.4}
          for n in list(bk.JOINT_NAMES)[:1]}
verdict = feas.build_feasibility_report(saturation=bk_sat)
assert verdict["verdict"] == feas.INFEASIBLE
print(f"cross-check verdict on Berkeley sat data: {verdict['verdict']} "
      f"({verdict['worst_joint']})")
print("PASS — physical-fidelity tooling is robot-agnostic; runs on both the G1 "
      "and the Berkeley Humanoid Lite spec profiles")
