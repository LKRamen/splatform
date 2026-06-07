"""Per-joint actuator saturation logging (PF-1).

Records, per joint per episode, how hard each actuator is being pushed against
its real Unitree G1 limits: peak |torque|, fraction of peak rating used, and how
many steps it spent within ``near_limit_frac`` of the limit (a "saturation
event"). The same is tracked for joint velocity.

Torque limits are authoritative (read from the MJCF via g1_specs). Velocity
limits are an ASSUMPTION (see g1_specs) and are therefore a *relative* signal.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np


class SaturationLogger:
    """Accumulates per-joint torque/velocity saturation stats over an episode."""

    def __init__(
        self,
        joint_names: List[str],
        peak_torque_nm: np.ndarray,
        velocity_limit_rad_s: np.ndarray,
        near_limit_frac: float = 0.02,
    ) -> None:
        if not (0.0 < near_limit_frac < 1.0):
            raise ValueError(f"near_limit_frac must be in (0,1), got {near_limit_frac}")
        n = len(joint_names)
        if peak_torque_nm.shape != (n,) or velocity_limit_rad_s.shape != (n,):
            raise ValueError("limit arrays must match joint_names length")
        if np.any(peak_torque_nm <= 0) or np.any(velocity_limit_rad_s <= 0):
            raise ValueError("limits must be strictly positive")

        self._names = list(joint_names)
        self._peak = peak_torque_nm.astype(np.float64)
        self._vlim = velocity_limit_rad_s.astype(np.float64)
        self._near = float(near_limit_frac)
        self.reset()

    def reset(self) -> None:
        """Clear all accumulated stats. Call on env reset."""
        n = len(self._names)
        self._steps = 0
        self._peak_torque = np.zeros(n)
        self._peak_vel = np.zeros(n)
        self._torque_sat_steps = np.zeros(n, dtype=np.int64)
        self._vel_sat_steps = np.zeros(n, dtype=np.int64)

    def update(self, torque: np.ndarray, velocity: np.ndarray) -> None:
        """Record one step. ``torque`` and ``velocity`` are per-joint arrays.

        ``torque`` is the realised actuator force (N·m); ``velocity`` the joint
        angular velocity (rad/s), both in joint order.
        """
        abs_t = np.abs(np.asarray(torque, dtype=np.float64))
        abs_v = np.abs(np.asarray(velocity, dtype=np.float64))
        if abs_t.shape != self._peak.shape or abs_v.shape != self._vlim.shape:
            raise ValueError("torque/velocity shape mismatch with configured joints")

        self._steps += 1
        self._peak_torque = np.maximum(self._peak_torque, abs_t)
        self._peak_vel = np.maximum(self._peak_vel, abs_v)
        self._torque_sat_steps += (abs_t >= (1.0 - self._near) * self._peak).astype(np.int64)
        self._vel_sat_steps += (abs_v >= (1.0 - self._near) * self._vlim).astype(np.int64)

    @property
    def steps(self) -> int:
        return self._steps

    def report(self) -> Dict[str, Dict[str, float]]:
        """Per-joint dict of saturation stats (fresh objects, safe to mutate)."""
        steps = max(self._steps, 1)
        out: Dict[str, Dict[str, float]] = {}
        for i, name in enumerate(self._names):
            out[name] = {
                "peak_torque_nm": float(self._peak_torque[i]),
                "peak_torque_pct": float(100.0 * self._peak_torque[i] / self._peak[i]),
                "torque_saturation_steps": int(self._torque_sat_steps[i]),
                "torque_saturation_frac": float(self._torque_sat_steps[i] / steps),
                "peak_vel_rad_s": float(self._peak_vel[i]),
                "peak_vel_pct": float(100.0 * self._peak_vel[i] / self._vlim[i]),
                "vel_saturation_steps": int(self._vel_sat_steps[i]),
                "vel_saturation_frac": float(self._vel_sat_steps[i] / steps),
            }
        return out

    def worst_joint(self) -> tuple[str, float]:
        """(joint_name, peak_torque_pct) for the most-stressed joint."""
        if not self._names:
            return ("", 0.0)
        pct = 100.0 * self._peak_torque / self._peak
        i = int(np.argmax(pct))
        return (self._names[i], float(pct[i]))

    def summary_str(self, warn_pct: float = 80.0) -> str:
        """Compact multi-line summary; flags joints above ``warn_pct`` of peak."""
        rep = self.report()
        lines = [f"[saturation] {self._steps} steps — torque/velocity vs G1 limits"]
        flagged = False
        for name, r in rep.items():
            mark = ""
            if r["peak_torque_pct"] >= warn_pct or r["peak_vel_pct"] >= warn_pct:
                mark = "  <-- HIGH"
                flagged = True
            lines.append(
                f"  {name:26s} torque {r['peak_torque_pct']:5.1f}%peak "
                f"({r['torque_saturation_steps']:4d} sat)  "
                f"vel {r['peak_vel_pct']:5.1f}%lim "
                f"({r['vel_saturation_steps']:4d} sat){mark}"
            )
        if not flagged:
            lines.append("  no joint exceeded "
                         f"{warn_pct:.0f}% of peak torque or velocity limit")
        return "\n".join(lines)
