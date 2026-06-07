# Physical validation — cross-checking our feasibility model (PF-9)

A fair question from a judge: *"Your feasibility thresholds use some assumed
numbers (continuous torque, efficiency, velocity limits). How do we know the
verdicts mean anything?"*

This note answers that by comparing our approach, **in spirit**, to a robot whose
hardware is published end-to-end: **Berkeley Humanoid Lite**
([project](https://lite.berkeley-humanoid.org/),
[arXiv 2504.17249](https://arxiv.org/abs/2504.17249)) — an open-source,
3D-printed humanoid with fully documented actuators, battery, and firmware.

## What is grounded vs assumed in our G1 model

| Quantity | Our G1 source | Confidence |
|----------|---------------|------------|
| Peak joint torque | **Read from the MJCF** (`jnt_actfrcrange`) | grounded |
| Joint position limits | **Read from the MJCF** | grounded |
| Mass | published ~35 kg (model sums ~33 kg) | grounded |
| Battery energy | published 9 Ah × 54 V → ~486 Wh | grounded |
| Continuous (thermal) torque | **0.35 × peak — ASSUMPTION** | relative only |
| Drivetrain efficiency | **0.7 — ASSUMPTION** | relative only |
| Per-joint velocity limit | **30 rad/s — ASSUMPTION** | relative only |

The feasibility verdict (PF-7) leans hardest on the **grounded** numbers
(torque saturation, tipping, payload moment vs. peak torque) and treats the
**assumed** ones (thermal, runtime) as *relative warnings*, with explicit caveats
in the output. So an INFEASIBLE verdict driven by "knee pinned at peak torque 90%
of steps" is a hard, model-grounded fact; a MARGINAL driven by thermal duty cycle
is flagged as assumption-based.

## Why Berkeley Humanoid Lite is a useful yardstick

Berkeley Lite publishes the things Unitree does not (continuous ratings, gear
design, battery chemistry), and it is a *much* smaller robot (16 kg, 0.8 m, 6S
4 Ah ≈ 89 Wh, ~30 min runtime, 3D-printed cycloidal actuators). Our feasibility
*rules* — torque-headroom %, a duty-cycle RMS check, a payload-moment fraction,
a CoM-in-support-polygon test — are the same kinds of checks a team with full
specs would apply; only the numbers differ. The thresholds are expressed as
**fractions of each robot's own ratings**, so they transfer across robots rather
than hard-coding G1-specific magnitudes.

## The tooling generalizes (demonstrated)

`src/backend/berkeley_lite_specs.py` is a second spec profile exposing the same
interface as `g1_specs` (`peak_torque_array()`, `continuous_torque_array()`,
`velocity_limit_array()`, battery/mass/payload constants). Because the physical
loggers and `feasibility.build_feasibility_report()` consume those arrays rather
than G1 constants, the exact same tooling can be pointed at Berkeley Lite — see
`test_cross_check.py`. (Berkeley per-joint torques are not in the cited source,
so that profile's torques are flagged APPROX; its mass/height/battery are
published.)

**Takeaway for judges:** the feasibility engine is robot-agnostic and leans on
model-grounded limits; the assumed numbers are isolated, labeled, and only ever
downgrade a verdict to MARGINAL with a caveat — never silently to FEASIBLE.
