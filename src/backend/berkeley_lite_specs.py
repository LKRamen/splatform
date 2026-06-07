"""Second robot spec profile — Berkeley Humanoid Lite (PF-9, stretch).

Demonstrates that the physical-fidelity tooling (saturation / power / thermal /
stability / feasibility) is robot-agnostic: it consumes a spec module's arrays,
so pointing it at a different robot is just swapping this profile in.

Berkeley Humanoid Lite is a fully open hardware+firmware+software humanoid
(HybridRobotics/Berkeley-Humanoid-Lite, arXiv 2504.17249) — useful precisely
because its hardware is published end-to-end.

Honesty tiers (same discipline as g1_specs):
  * PUBLISHED — mass 16 kg, height 0.8 m, 6S 4 Ah LiPo (~88.8 Wh nominal),
    ~30 min runtime, 3D-printed cycloidal-gearbox actuators in two sizes.
  * APPROX — per-joint peak torques are NOT in the cited source, so the values
    below are a *representative* two-size profile (large leg / small arm) for the
    tooling-generalization demo only. Do not treat them as official.

Source: https://lite.berkeley-humanoid.org/ , https://arxiv.org/abs/2504.17249
"""
from __future__ import annotations

from typing import Dict, Tuple

import numpy as np

# Representative 22-DOF layout (APPROX — for tooling generalization only).
JOINT_NAMES: Tuple[str, ...] = (
    "left_hip_yaw", "left_hip_roll", "left_hip_pitch", "left_knee",
    "left_ankle_pitch", "left_ankle_roll",
    "right_hip_yaw", "right_hip_roll", "right_hip_pitch", "right_knee",
    "right_ankle_pitch", "right_ankle_roll",
    "waist_yaw",
    "left_shoulder_pitch", "left_shoulder_roll", "left_elbow", "left_wrist",
    "right_shoulder_pitch", "right_shoulder_roll", "right_elbow", "right_wrist",
    "head_yaw",
)
NUM_DOF: int = len(JOINT_NAMES)  # 22

# APPROX two-size cycloidal actuator profile (N·m). Legs/knee use the large
# actuator, arms/waist/head the small one. Representative, not published.
_LARGE_TORQUE = 12.0  # APPROX
_SMALL_TORQUE = 6.0   # APPROX
_LARGE_JOINTS = {
    "left_hip_roll", "left_hip_pitch", "left_knee",
    "right_hip_roll", "right_hip_pitch", "right_knee",
}
PEAK_TORQUE_NM: Dict[str, float] = {
    name: (_LARGE_TORQUE if name in _LARGE_JOINTS else _SMALL_TORQUE)
    for name in JOINT_NAMES
}

CONTINUOUS_TORQUE_FRACTION: float = 0.35  # ASSUMPTION (same discipline as G1)
CONTINUOUS_TORQUE_NM: Dict[str, float] = {
    n: round(CONTINUOUS_TORQUE_FRACTION * t, 3) for n, t in PEAK_TORQUE_NM.items()
}

ASSUMED_VELOCITY_LIMIT_RAD_S: float = 20.0  # ASSUMPTION (3D-printed cycloidal)
VELOCITY_LIMIT_RAD_S: Dict[str, float] = {n: ASSUMED_VELOCITY_LIMIT_RAD_S for n in JOINT_NAMES}

MASS_KG: float = 16.0          # published
HEIGHT_M: float = 0.8          # published
HAS_HANDS: bool = False        # open arms, no dexterous hands by default

# 6S LiPo, 4 Ah: nominal 6*3.7 V = 22.2 V; Wh = 22.2 * 4 = 88.8 (published cells).
BATTERY_AH: float = 4.0        # published
BATTERY_V_NOMINAL: float = 22.2
BATTERY_WH: float = round(BATTERY_AH * BATTERY_V_NOMINAL, 1)  # ~88.8 Wh
CONTINUOUS_PAYLOAD_KG: Tuple[float, float] = (0.5, 1.0)  # APPROX (small robot)


def peak_torque_array() -> np.ndarray:
    return np.array([PEAK_TORQUE_NM[n] for n in JOINT_NAMES], dtype=np.float64)


def continuous_torque_array() -> np.ndarray:
    return np.array([CONTINUOUS_TORQUE_NM[n] for n in JOINT_NAMES], dtype=np.float64)


def velocity_limit_array() -> np.ndarray:
    return np.array([VELOCITY_LIMIT_RAD_S[n] for n in JOINT_NAMES], dtype=np.float64)
