"""Single source of truth for real Unitree G1 hardware numbers.

Every physical-fidelity check (PF-1..PF-8) imports limits from here instead of
hardcoding. Values are split into two honesty tiers:

  * MODEL  — read directly from the MuJoCo Menagerie model
    (``mujoco_menagerie/unitree_g1/g1.xml``). These are authoritative for the
    physics that actually runs: peak joint torque (``jnt_actfrcrange``) and
    joint position ranges (``jnt_range``). ``verify_against_model()`` asserts the
    baked constants still match the loaded model so they cannot silently drift.
  * PUBLISHED / ASSUMPTION — Unitree's public spec sheet, or, where Unitree does
    not publish a number, a clearly-flagged placeholder. Anything marked
    ASSUMPTION is logged in PROGRESS.md.

Sources:
  * MuJoCo Menagerie unitree_g1 (BSD-3) — masses/inertias/limits.
  * Unitree G1 public specs — https://www.unitree.com/g1
    (mass ~35 kg, height ~1.32 m, 13S 9 Ah battery w/ 54 V charger,
    base 23-DOF / this model 29-DOF / EDU up to 43-DOF, ~2 kg per-arm payload).
"""
from __future__ import annotations

import os
from typing import Dict, Tuple

import numpy as np

# --- Model location (same file the live env loads) -------------------------
XML_PATH = os.path.join(
    os.path.dirname(__file__), "../../mujoco_menagerie/unitree_g1/g1.xml"
)

# --- Joint order ------------------------------------------------------------
# MJCF actuator order == G1TraversalEnv action order == WebSocket joint order.
# This is the 29-DOF G1 variant (base G1 is 23-DOF; EDU Ultimate up to 43-DOF).
JOINT_NAMES: Tuple[str, ...] = (
    "left_hip_pitch_joint",
    "left_hip_roll_joint",
    "left_hip_yaw_joint",
    "left_knee_joint",
    "left_ankle_pitch_joint",
    "left_ankle_roll_joint",
    "right_hip_pitch_joint",
    "right_hip_roll_joint",
    "right_hip_yaw_joint",
    "right_knee_joint",
    "right_ankle_pitch_joint",
    "right_ankle_roll_joint",
    "waist_yaw_joint",
    "waist_roll_joint",
    "waist_pitch_joint",
    "left_shoulder_pitch_joint",
    "left_shoulder_roll_joint",
    "left_shoulder_yaw_joint",
    "left_elbow_joint",
    "left_wrist_roll_joint",
    "left_wrist_pitch_joint",
    "left_wrist_yaw_joint",
    "right_shoulder_pitch_joint",
    "right_shoulder_roll_joint",
    "right_shoulder_yaw_joint",
    "right_elbow_joint",
    "right_wrist_roll_joint",
    "right_wrist_pitch_joint",
    "right_wrist_yaw_joint",
)

NUM_DOF: int = len(JOINT_NAMES)  # 29

# --- Peak joint torque (N·m) -----------------------------------------------
# MODEL: read from g1.xml <joint actuatorfrcrange="..."> (verified at import-time
# friendly helper verify_against_model()). These are the limits MuJoCo actually
# enforces (jnt_actfrclimited=True), so they are the honest peak ratings.
# Cross-check vs Unitree marketing: base-G1 knee is advertised ~90 N·m and
# EDU-knee ~120 N·m; the menagerie model encodes 139 N·m for hip-roll/knee. We
# use the MODEL value because that is what the simulated physics obeys.
PEAK_TORQUE_NM: Dict[str, float] = {
    "left_hip_pitch_joint": 88.0,
    "left_hip_roll_joint": 139.0,
    "left_hip_yaw_joint": 88.0,
    "left_knee_joint": 139.0,
    "left_ankle_pitch_joint": 50.0,
    "left_ankle_roll_joint": 50.0,
    "right_hip_pitch_joint": 88.0,
    "right_hip_roll_joint": 139.0,
    "right_hip_yaw_joint": 88.0,
    "right_knee_joint": 139.0,
    "right_ankle_pitch_joint": 50.0,
    "right_ankle_roll_joint": 50.0,
    "waist_yaw_joint": 88.0,
    "waist_roll_joint": 50.0,
    "waist_pitch_joint": 50.0,
    "left_shoulder_pitch_joint": 25.0,
    "left_shoulder_roll_joint": 25.0,
    "left_shoulder_yaw_joint": 25.0,
    "left_elbow_joint": 25.0,
    "left_wrist_roll_joint": 25.0,
    "left_wrist_pitch_joint": 5.0,
    "left_wrist_yaw_joint": 5.0,
    "right_shoulder_pitch_joint": 25.0,
    "right_shoulder_roll_joint": 25.0,
    "right_shoulder_yaw_joint": 25.0,
    "right_elbow_joint": 25.0,
    "right_wrist_roll_joint": 25.0,
    "right_wrist_pitch_joint": 5.0,
    "right_wrist_yaw_joint": 5.0,
}

# --- Continuous torque (N·m) -----------------------------------------------
# ASSUMPTION: Unitree does NOT publish continuous (thermal) torque ratings.
# Placeholder = 0.35 * peak. Used only for the PF-3 duty-cycle warning, which is
# explicitly a *relative* signal, not an absolute thermal model. Logged in
# PROGRESS.md.
CONTINUOUS_TORQUE_FRACTION: float = 0.35  # ASSUMPTION
CONTINUOUS_TORQUE_NM: Dict[str, float] = {
    name: round(CONTINUOUS_TORQUE_FRACTION * peak, 3)
    for name, peak in PEAK_TORQUE_NM.items()
}

# --- Velocity limits (rad/s) -----------------------------------------------
# ASSUMPTION: MuJoCo joints carry no velocity-limit field, and Unitree does not
# publish clean per-joint max angular velocities. We use a single conservative
# default across joints. Treated as a relative saturation signal only. Logged
# in PROGRESS.md.
ASSUMED_VELOCITY_LIMIT_RAD_S: float = 30.0  # ASSUMPTION
VELOCITY_LIMIT_RAD_S: Dict[str, float] = {
    name: ASSUMED_VELOCITY_LIMIT_RAD_S for name in JOINT_NAMES
}

# --- Whole-body / published numbers ----------------------------------------
MASS_KG: float = 35.0          # published (incl. battery); model sums to ~33.3 kg
MODEL_MASS_KG: float = 33.34   # MODEL: sum of body masses in g1.xml (reference)
HEIGHT_M: float = 1.32         # published standing height
ARM_DOF_PER_SIDE: int = 7      # shoulder p/r/y + elbow + wrist r/p/y (29-DOF G1)
HAS_HANDS: bool = False        # base/this model has no actuated fingers (cannot grasp)

# --- Battery ---------------------------------------------------------------
# Published: 13S smart Li battery, 9 Ah, 54 V charger. Wh derived from Ah * V.
# 54 V is the charge/max voltage; nominal (13 * 3.6 ≈ 47 V) gives ~423 Wh, so the
# real usable energy sits ~423-486 Wh. We keep the 54 V-derived figure and note
# the spread.
BATTERY_AH: float = 9.0        # published
BATTERY_V_MAX: float = 54.0    # published (charger voltage)
BATTERY_WH: float = round(BATTERY_AH * BATTERY_V_MAX, 1)  # ~486 Wh (max-V derived)

# --- Payload ---------------------------------------------------------------
# Published: ~2 kg per arm (base), ~3 kg per arm (EDU Ultimate). Expressed as a
# (base, ultimate) per-arm range. Base G1 cannot grasp (HAS_HANDS=False); see
# DEX hand note below and PF-8.
PAYLOAD_PER_ARM_KG: float = 2.0            # published, base
CONTINUOUS_PAYLOAD_KG: Tuple[float, float] = (2.0, 3.0)  # (base, ultimate) per arm

# A dexterous-hand add-on (e.g. Unitree Dex3/Dex5) is required to grasp at all.
# Tasks opt into this explicitly (PF-8); payload capped low when assumed.
DEX_HAND_PAYLOAD_KG: float = 2.0           # ASSUMPTION (add-on; not on base G1)


# --- Ordered-array accessors -----------------------------------------------
def peak_torque_array() -> np.ndarray:
    """Peak torque (N·m) per joint, in JOINT_NAMES order."""
    return np.array([PEAK_TORQUE_NM[n] for n in JOINT_NAMES], dtype=np.float64)


def continuous_torque_array() -> np.ndarray:
    """Continuous (ASSUMPTION) torque (N·m) per joint, in JOINT_NAMES order."""
    return np.array([CONTINUOUS_TORQUE_NM[n] for n in JOINT_NAMES], dtype=np.float64)


def velocity_limit_array() -> np.ndarray:
    """Velocity limit (ASSUMPTION, rad/s) per joint, in JOINT_NAMES order."""
    return np.array([VELOCITY_LIMIT_RAD_S[n] for n in JOINT_NAMES], dtype=np.float64)


def verify_against_model(model=None) -> None:
    """Assert baked MODEL constants still match the loaded MuJoCo model.

    Guards against silent drift if the menagerie model is updated. Raises
    AssertionError with the offending joint if peak torque or joint order
    diverges. ``model`` may be a preloaded ``mujoco.MjModel``.
    """
    import mujoco  # local import: keep module importable without a model load

    if model is None:
        model = mujoco.MjModel.from_xml_path(XML_PATH)

    assert model.nu == NUM_DOF, f"model.nu={model.nu} != NUM_DOF={NUM_DOF}"

    for i, name in enumerate(JOINT_NAMES):
        act_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
        assert act_name == name, f"actuator {i}: model={act_name!r} spec={name!r}"
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        lo, hi = model.jnt_actfrcrange[jid]
        # Symmetric ratings expected; compare the magnitude.
        model_peak = float(max(abs(lo), abs(hi)))
        assert abs(model_peak - PEAK_TORQUE_NM[name]) < 1e-6, (
            f"{name}: model peak {model_peak} != spec {PEAK_TORQUE_NM[name]}"
        )
