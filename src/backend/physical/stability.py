"""Stability & payload feasibility (PF-6).

Two checks:

  * Tipping — each step we compute the robot centre of mass and the support
    polygon (convex hull of the active foot-floor contact points). If the CoM's
    ground projection leaves the support polygon the robot is tipping; we report
    the worst (most negative) margin and the number of violating steps.
  * Payload — when the robot carries an object, the static moment at the
    shoulder (mass * g * horizontal_arm_extension) is compared to the arm joint
    peak torque (G1 ~25 N·m). We flag if it exceeds 60% of the rating (headroom
    for dynamics), and if carried mass exceeds the continuous payload range.

Geometry is pure-numpy (convex hull via monotone chain) to avoid a scipy dep.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

G = 9.81


def convex_hull(points: np.ndarray) -> np.ndarray:
    """CCW convex hull of 2-D points (Andrew's monotone chain)."""
    pts = np.unique(np.asarray(points, dtype=np.float64).reshape(-1, 2), axis=0)
    if len(pts) <= 2:
        return pts
    pts = pts[np.lexsort((pts[:, 1], pts[:, 0]))]

    def _half(ps):
        h: List[np.ndarray] = []
        for p in ps:
            while len(h) >= 2 and np.cross(h[-1] - h[-2], p - h[-2]) <= 0:
                h.pop()
            h.append(p)
        return h[:-1]

    lower = _half(pts)
    upper = _half(pts[::-1])
    return np.array(lower + upper)


def support_margin(point: np.ndarray, hull: np.ndarray) -> float:
    """Signed distance from ``point`` to the support polygon boundary.

    Positive when inside (distance to nearest edge), negative when outside.
    Degenerates gracefully for empty / point / line supports.
    """
    p = np.asarray(point, dtype=np.float64)
    if len(hull) == 0:
        return float("-inf")
    if len(hull) == 1:
        return -float(np.linalg.norm(p - hull[0]))
    if len(hull) == 2:
        return -_dist_to_segment(p, hull[0], hull[1])

    margins = []
    n = len(hull)
    for i in range(n):
        a, b = hull[i], hull[(i + 1) % n]
        edge = b - a
        length = np.linalg.norm(edge)
        if length < 1e-12:
            continue
        # CCW hull: positive cross => point left of edge => inside side.
        margins.append(float(np.cross(edge, p - a) / length))
    if not margins:
        return float("-inf")
    return min(margins)


def _dist_to_segment(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    ab = b - a
    denom = float(ab @ ab)
    t = 0.0 if denom < 1e-12 else float(np.clip((p - a) @ ab / denom, 0.0, 1.0))
    return float(np.linalg.norm(p - (a + t * ab)))


class StabilityLogger:
    """Per-episode tipping and payload feasibility accumulator."""

    def __init__(
        self,
        arm_peak_torque_nm: float,
        payload_range_kg: tuple,
        moment_warn_frac: float = 0.60,
    ) -> None:
        if arm_peak_torque_nm <= 0:
            raise ValueError("arm_peak_torque_nm must be positive")
        self._arm_peak = float(arm_peak_torque_nm)
        self._payload_lo, self._payload_hi = payload_range_kg
        self._warn = float(moment_warn_frac)
        self.reset()

    @property
    def steps(self) -> int:
        return self._steps

    def reset(self) -> None:
        self._steps = 0
        self._tipping_violations = 0
        self._min_margin = float("inf")
        self._max_moment_pct = 0.0
        self._max_carried_mass = 0.0
        self._payload_ok = True

    def update_stability(self, com_xy: np.ndarray, hull: np.ndarray) -> float:
        """Record one step's CoM/support; returns the support margin."""
        margin = support_margin(com_xy, hull)
        self._steps += 1
        if np.isfinite(margin):
            self._min_margin = min(self._min_margin, margin)
        else:
            self._min_margin = -np.inf
        if margin < 0:
            self._tipping_violations += 1
        return margin

    def update_payload(self, carried_mass_kg: float, arm_extension_m: float) -> None:
        """Record a carried-object payload check (call when carrying)."""
        moment = carried_mass_kg * G * max(arm_extension_m, 0.0)
        pct = 100.0 * moment / self._arm_peak
        self._max_moment_pct = max(self._max_moment_pct, pct)
        self._max_carried_mass = max(self._max_carried_mass, carried_mass_kg)
        within_torque = pct <= 100.0 * self._warn
        within_mass = carried_mass_kg <= self._payload_hi
        if not (within_torque and within_mass):
            self._payload_ok = False

    def report(self) -> Dict[str, Optional[float]]:
        """Stability section for the feasibility report (fresh dict)."""
        min_margin = None if self._min_margin == float("inf") else float(self._min_margin)
        return {
            "tipping_violations": int(self._tipping_violations),
            "tipping_violation_frac": float(self._tipping_violations / max(self._steps, 1)),
            "min_support_margin_m": min_margin,
            "shoulder_moment_pct_of_limit": float(self._max_moment_pct),
            "max_carried_mass_kg": float(self._max_carried_mass),
            "payload_ok": bool(self._payload_ok),
        }

    def summary_str(self) -> str:
        r = self.report()
        mm = r["min_support_margin_m"]
        mm_s = "n/a" if mm is None else f"{mm:+.3f} m"
        return (
            f"[stability] tipping {r['tipping_violations']}/{self._steps} steps  "
            f"min support margin {mm_s}  "
            f"shoulder moment {r['shoulder_moment_pct_of_limit']:.1f}% of limit  "
            f"payload_ok={r['payload_ok']}"
        )
