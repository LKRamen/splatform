"""Aggregate feasibility verdict (PF-7).

Collapses the PF-1..PF-6 sections (saturation, power, thermal, stability) into a
single verdict per task run — FEASIBLE / MARGINAL / INFEASIBLE — answering the
phase's core question: "could the real Unitree G1 actually do this?"

Thresholds (documented, tunable):
  * SAT_TORQUE_INFEASIBLE_FRAC = 0.20 — a joint pinned at peak torque for >20% of
    steps cannot be held by a real motor → INFEASIBLE; >5% → MARGINAL.
  * TIPPING_INFEASIBLE_FRAC = 0.05 — CoM outside the support polygon >5% of steps
    → INFEASIBLE; any tipping at all → MARGINAL.
  * THERMAL_INFEASIBLE_DURATION_S = 1.0 — windowed RMS torque over the (ASSUMED)
    continuous rating for ≥1 s → INFEASIBLE; briefer → MARGINAL. NB: continuous
    ratings are assumptions, so thermal alone is treated cautiously.
  * RUNTIME_MARGINAL_MIN = 30 — estimated battery runtime under 30 min → MARGINAL.
  * payload_ok False (shoulder moment >60% of arm peak, or mass over the
    continuous payload range) → INFEASIBLE.
"""
from __future__ import annotations

import json
import os
import time
from typing import Dict, Optional

SAT_TORQUE_INFEASIBLE_FRAC = 0.20
SAT_TORQUE_MARGINAL_FRAC = 0.05
TIPPING_INFEASIBLE_FRAC = 0.05
THERMAL_INFEASIBLE_DURATION_S = 1.0
RUNTIME_MARGINAL_MIN = 30.0

FEASIBLE = "FEASIBLE"
MARGINAL = "MARGINAL"
INFEASIBLE = "INFEASIBLE"
NA = "N/A"


def build_feasibility_report(
    saturation: Optional[Dict] = None,
    power: Optional[Dict] = None,
    thermal: Optional[Dict] = None,
    stability: Optional[Dict] = None,
) -> Dict:
    """Combine available sections into a verdict + reason + worst joint."""
    infeasible, marginal = [], []
    worst_joint, worst_pct = None, -1.0

    if saturation:
        for name, r in saturation.items():
            if r["peak_torque_pct"] > worst_pct:
                worst_pct, worst_joint = r["peak_torque_pct"], name
            frac = r["torque_saturation_frac"]
            if frac > SAT_TORQUE_INFEASIBLE_FRAC:
                infeasible.append(f"{name} at peak torque {frac * 100:.0f}% of steps")
            elif frac > SAT_TORQUE_MARGINAL_FRAC:
                marginal.append(f"{name} near peak torque {frac * 100:.0f}% of steps")

    if thermal:
        for name, r in thermal.items():
            if not r["overheat_risk"]:
                continue
            if r["over_duration_s"] >= THERMAL_INFEASIBLE_DURATION_S:
                infeasible.append(
                    f"{name} over continuous rating for {r['over_duration_s']:.1f}s")
            else:
                marginal.append(
                    f"{name} brief thermal over-rating ({r['over_duration_s']:.2f}s)")

    if stability:
        tv_frac = stability.get("tipping_violation_frac", 0.0)
        if tv_frac > TIPPING_INFEASIBLE_FRAC:
            infeasible.append(f"tipping (CoM outside support) {tv_frac * 100:.0f}% of steps")
        elif stability.get("tipping_violations", 0) > 0:
            marginal.append("occasional loss of support margin")
        if stability.get("payload_ok", True) is False:
            infeasible.append("payload exceeds arm torque / mass limit")

    if power:
        rt = power.get("est_runtime_min")
        if rt is not None and rt != float("inf") and rt < RUNTIME_MARGINAL_MIN:
            marginal.append(f"battery runtime ~{rt:.0f} min")

    has_data = any(s is not None for s in (saturation, power, thermal, stability))
    if not has_data:
        verdict, reason = NA, "no physics data (preview mode)"
    elif infeasible:
        verdict, reason = INFEASIBLE, infeasible[0]
    elif marginal:
        verdict, reason = MARGINAL, marginal[0]
    else:
        verdict, reason = FEASIBLE, "within all hardware limits"

    return {
        "verdict": verdict,
        "reason": reason,
        "worst_joint": worst_joint,
        "reasons": {"infeasible": infeasible, "marginal": marginal},
        "sections": {
            "saturation": saturation,
            "power": power,
            "thermal": thermal,
            "stability": stability,
        },
    }


def compact(report: Dict) -> Dict:
    """Minimal live payload for the WebSocket frame."""
    return {
        "verdict": report["verdict"],
        "reason": report["reason"],
        "worst_joint": report["worst_joint"],
    }


def save_feasibility_report(report: Dict, checkpoint_dir: str, ckpt_name: str) -> str:
    """Write the full report as JSON under <checkpoint_dir>/<ckpt>/feasibility/."""
    out_dir = os.path.join(checkpoint_dir, ckpt_name, "feasibility")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{int(time.time())}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    return path
