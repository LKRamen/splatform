import numpy as np
import mujoco


def waypoint_efficiency_reward(dist: float, prev_dist: float, step: int) -> float:
    """Progress toward current waypoint per step. Range roughly [-1, 1]."""
    progress = prev_dist - dist       # positive = moving closer
    return float(np.clip(progress * 5.0, -1.0, 1.0))


def gait_stability_reward(pelvis_z: float, standing_z: float, quat: np.ndarray) -> float:
    """Penalise height deviation from standing and excessive tilt. Range [-1, 1]."""
    height_err = abs(pelvis_z - standing_z)
    w, x, y, z = quat
    # Tilt magnitude: deviation from upright
    tilt = 1.0 - abs(w)    # 0 = upright, 1 = 180° tipped
    score = 1.0 - np.clip(height_err * 4.0 + tilt * 2.0, 0.0, 2.0)
    return float(score)


def clearance_reward(data: 'mujoco.MjData', model: 'mujoco.MjModel') -> float:
    """Reward for not being in contact with obstacles. Range [0, 1]."""
    # Use number of active contacts as proxy; fewer = better clearance
    n_contacts = data.ncon
    # No contacts = 1.0; many contacts = approaching 0
    score = 1.0 / (1.0 + 0.5 * max(0, n_contacts - 2))  # allow foot contacts
    return float(score)


def energy_reward(actuator_force: np.ndarray) -> float:
    """Penalise high torques. Range [-1, 0]."""
    torque_sq = float(np.sum(actuator_force ** 2))
    return float(-np.log1p(torque_sq * 0.001))


def completion_reward(reached_all: bool) -> float:
    """Sparse reward for completing all waypoints."""
    return 10.0 if reached_all else 0.0
