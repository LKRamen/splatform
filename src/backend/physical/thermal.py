"""Thermal duty-cycle check (PF-3).

MuJoCo models no heat, so this is a post-hoc duty-cycle proxy. The risk is not a
brief torque spike (peak torque is fine for a moment) but *sustained* near-peak
torque. We compute a sliding-window RMS torque per joint and compare it to the
joint's continuous rating: windowed RMS above the continuous rating is flagged
as a THERMAL RISK, with the duration it stayed over.

IMPORTANT CAVEAT: continuous ratings are an ASSUMPTION (0.35 * peak; Unitree
does not publish them). Treat overheat flags as a *relative* warning about
duty cycle, not an absolute thermal prediction.
"""
from __future__ import annotations

from collections import deque
from typing import Dict

import numpy as np


class ThermalLogger:
    """Sliding-window RMS torque vs continuous rating, per joint."""

    def __init__(
        self,
        continuous_torque_nm: np.ndarray,
        dt: float,
        window_s: float = 2.0,
    ) -> None:
        if dt <= 0:
            raise ValueError(f"dt must be positive, got {dt}")
        if window_s <= 0:
            raise ValueError(f"window_s must be positive, got {window_s}")
        if np.any(continuous_torque_nm <= 0):
            raise ValueError("continuous torque ratings must be positive")
        self._cont = np.asarray(continuous_torque_nm, dtype=np.float64)
        self._n = self._cont.shape[0]
        self._dt = float(dt)
        self._window_steps = max(1, int(round(window_s / dt)))
        self.reset()

    def reset(self) -> None:
        self._sq: deque = deque()        # recent squared-torque vectors
        self._sumsq = np.zeros(self._n)  # running sum over the window
        self._max_rms = np.zeros(self._n)
        self._over_steps = np.zeros(self._n, dtype=np.int64)

    def update(self, torque: np.ndarray) -> None:
        """Record one step's joint torque (N·m), maintain windowed RMS."""
        t = np.asarray(torque, dtype=np.float64)
        if t.shape != self._cont.shape:
            raise ValueError("torque shape mismatch with continuous ratings")
        sq = t * t
        self._sq.append(sq)
        self._sumsq += sq
        if len(self._sq) > self._window_steps:
            self._sumsq -= self._sq.popleft()

        rms = np.sqrt(self._sumsq / len(self._sq))
        self._max_rms = np.maximum(self._max_rms, rms)
        self._over_steps += (rms > self._cont).astype(np.int64)

    def report(self) -> Dict[str, Dict[str, float]]:
        """Per-joint thermal stats (fresh objects)."""
        out: Dict[str, Dict[str, float]] = {}
        for i in range(self._n):
            out[str(i)] = {
                "max_windowed_rms_nm": float(self._max_rms[i]),
                "pct_of_continuous": float(100.0 * self._max_rms[i] / self._cont[i]),
                "overheat_risk": bool(self._over_steps[i] > 0),
                "over_duration_s": float(self._over_steps[i] * self._dt),
            }
        return out

    def report_named(self, joint_names) -> Dict[str, Dict[str, float]]:
        """Same as report() but keyed by joint name."""
        idx = self.report()
        return {name: idx[str(i)] for i, name in enumerate(joint_names)}

    def any_overheat(self) -> bool:
        return bool(np.any(self._over_steps > 0))

    def summary_str(self, joint_names) -> str:
        rep = self.report_named(joint_names)
        lines = [
            f"[thermal] {self._window_steps}-step ({self._window_steps * self._dt:.1f}s) "
            "windowed RMS torque vs CONTINUOUS rating",
            "  CAVEAT: continuous ratings are ASSUMPTIONS (0.35*peak); relative warning only",
        ]
        flagged = False
        for name, r in rep.items():
            if r["overheat_risk"]:
                flagged = True
                lines.append(
                    f"  {name:26s} RMS {r['pct_of_continuous']:6.1f}% of continuous "
                    f"for {r['over_duration_s']:.2f}s  <-- THERMAL RISK"
                )
        if not flagged:
            lines.append("  no joint exceeded its (assumed) continuous rating")
        return "\n".join(lines)
