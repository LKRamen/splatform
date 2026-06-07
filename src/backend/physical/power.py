"""Power & energy budget accounting (PF-2).

Per step, mechanical power per joint = torque * joint_velocity. Electrical draw
is estimated as P_elec = P_mech_positive / EFFICIENCY, where only positive
mechanical power counts — we do NOT assume regenerative recovery on braking
(negative mechanical power contributes zero). From the mean electrical draw and
the battery energy (g1_specs.BATTERY_WH) we estimate sustained runtime.

EFFICIENCY is an ASSUMPTION (0.7), logged in PROGRESS.md — Unitree does not
publish drivetrain efficiency.
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from src.backend import g1_specs


class PowerLogger:
    """Accumulates mechanical/electrical power over an episode."""

    def __init__(self, efficiency: float = 0.7, battery_wh: float = g1_specs.BATTERY_WH):
        if not (0.0 < efficiency <= 1.0):
            raise ValueError(f"efficiency must be in (0,1], got {efficiency}")
        if battery_wh <= 0:
            raise ValueError(f"battery_wh must be positive, got {battery_wh}")
        self._eff = float(efficiency)
        self._battery_wh = float(battery_wh)
        self.reset()

    def reset(self) -> None:
        self._peak_elec_w = 0.0
        self._energy_j = 0.0      # accumulated electrical energy (J)
        self._time_s = 0.0        # accumulated sim time (s)

    def update(self, torque: np.ndarray, velocity: np.ndarray, dt: float) -> None:
        """Record one step's power. torque/velocity are per-joint arrays."""
        if dt <= 0:
            raise ValueError(f"dt must be positive, got {dt}")
        torque = np.asarray(torque, dtype=np.float64)
        velocity = np.asarray(velocity, dtype=np.float64)
        if torque.shape != velocity.shape:
            raise ValueError("torque/velocity shape mismatch")

        p_mech_joint = torque * velocity            # signed, per joint (W)
        p_mech_draw = float(np.sum(np.maximum(p_mech_joint, 0.0)))  # no regen
        p_elec = p_mech_draw / self._eff

        self._peak_elec_w = max(self._peak_elec_w, p_elec)
        self._energy_j += p_elec * dt
        self._time_s += dt

    @property
    def mean_power_w(self) -> float:
        if self._time_s <= 0:
            return 0.0
        return self._energy_j / self._time_s

    def est_runtime_min(self) -> float:
        """Estimated sustained runtime (minutes) at this episode's mean draw."""
        mean_w = self.mean_power_w
        if mean_w <= 0:
            return float("inf")
        hours = self._battery_wh / mean_w
        return hours * 60.0

    def report(self) -> Dict[str, float]:
        """Power section for the feasibility report (fresh dict)."""
        return {
            "peak_power_w": float(self._peak_elec_w),
            "mean_power_w": float(self.mean_power_w),
            "est_runtime_min": float(self.est_runtime_min()),
            "efficiency": self._eff,            # ASSUMPTION
            "battery_wh": self._battery_wh,
        }

    def summary_str(self) -> str:
        r = self.report()
        rt = r["est_runtime_min"]
        rt_str = "inf (near-static)" if not np.isfinite(rt) else f"{rt:.1f} min"
        return (
            f"[power] peak {r['peak_power_w']:.0f} W  mean {r['mean_power_w']:.0f} W  "
            f"est runtime {rt_str}  (eff={r['efficiency']}, batt={r['battery_wh']:.0f} Wh)"
        )
