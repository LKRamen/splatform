"""Task manipulation capability model (PF-8) — hardware honesty.

The base Unitree G1 (and the 29-DOF model we run) has 4..7-DOF arms but **no
actuated fingers** (``g1_specs.HAS_HANDS == False``): it physically cannot grasp.
Any "manipulation" must therefore be either:

  * PUSH — move an object with arm/body contact along the ground (no lift, no
    grasp). This is what the base G1 can actually do.
  * CARRY_DEX_HAND — lift/carry, which only works if we *explicitly assume* a
    dexterous-hand add-on (Unitree Dex3/Dex5). Payload is then capped at
    ``g1_specs.DEX_HAND_PAYLOAD_KG`` (~2 kg) and the UI must label it
    "assumes Dex5 hand".

This module is the single place that codifies that policy plus push-based reward
helpers (reach + push progress, NO grasp term) and a per-task framing registry
with real-world context, so when the Phase 8 task envs are built they stay honest
about the hardware. Do NOT silently fake grasping.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

import numpy as np

from src.backend import g1_specs


class ManipulationMode(str, Enum):
    PUSH = "push"                      # arm/body contact, no grasp (base G1)
    CARRY_DEX_HAND = "carry_dex_hand"  # assumes a Dex hand add-on, <=2 kg


@dataclass(frozen=True)
class TaskCapability:
    """How a task manipulates objects, honestly w.r.t. G1 hardware."""

    task_id: str
    mode: ManipulationMode
    assumes_dex_hand: bool
    # None => no lift (push only); float => max liftable/carried mass (kg).
    max_object_mass_kg: Optional[float]
    description: str          # what the robot actually does (no grasp implied)
    real_world_context: str   # one line; base-G1 vs hand add-on distinction


def max_payload_kg(assumes_dex_hand: bool) -> float:
    """Max liftable mass: 0 without a hand (push only), else the Dex cap."""
    return g1_specs.DEX_HAND_PAYLOAD_KG if assumes_dex_hand else 0.0


# Per-task framing. box_sort / table_setup are push-based (no grasp);
# package_delivery opts into an assumed Dex5 hand and is mass-capped + labeled.
TASK_CAPABILITIES: Dict[str, TaskCapability] = {
    "box_sort": TaskCapability(
        task_id="box_sort",
        mode=ManipulationMode.PUSH,
        assumes_dex_hand=False,
        max_object_mass_kg=None,
        description="Push colored boxes to matching floor zones using arm/body "
                    "contact — no grasp (base G1 has no hands).",
        real_world_context="Warehouse sortation (Amazon Sequoia): base G1 can "
                           "push/nudge parcels; picking-and-placing needs a "
                           "dexterous-hand add-on.",
    ),
    "table_setup": TaskCapability(
        task_id="table_setup",
        mode=ManipulationMode.PUSH,
        assumes_dex_hand=False,
        max_object_mass_kg=None,
        description="Push objects (chair/cup/folder proxies) to marked target "
                    "positions with arm/body contact — no grasp.",
        real_world_context="Office service robots: base G1 can reposition items "
                           "by pushing; precise placement/grasping assumes a hand.",
    ),
    "package_delivery": TaskCapability(
        task_id="package_delivery",
        mode=ManipulationMode.CARRY_DEX_HAND,
        assumes_dex_hand=True,
        max_object_mass_kg=g1_specs.DEX_HAND_PAYLOAD_KG,  # ~2 kg, labeled
        description="Carry a <=2 kg package A->B. ASSUMES a Dex5 hand add-on "
                    "(base G1 cannot grasp); object mass is capped accordingly.",
        real_world_context="Last-mile humanoid delivery (Figure/1X): requires a "
                           "dexterous hand — flagged 'assumes Dex5 hand' in the UI.",
    ),
}


def get_capability(task_id: str) -> TaskCapability:
    if task_id not in TASK_CAPABILITIES:
        raise KeyError(f"unknown task_id {task_id!r}")
    return TASK_CAPABILITIES[task_id]


def validate_object_mass(task_id: str, mass_kg: float) -> bool:
    """True if ``mass_kg`` is feasible for the task's capability.

    Push tasks: any mass is allowed (it slides, no lift). Carry tasks: mass must
    not exceed the assumed Dex-hand payload cap.
    """
    cap = get_capability(task_id)
    if cap.max_object_mass_kg is None:
        return True
    return mass_kg <= cap.max_object_mass_kg + 1e-9


# --- push-based reward helpers (reach + push; NO grasp term) ----------------
def reach_object_reward(effector_xy: np.ndarray, object_xy: np.ndarray,
                        scale: float = 1.0) -> float:
    """In [0,1]: how close the pushing effector is to the object."""
    d = float(np.linalg.norm(np.asarray(effector_xy) - np.asarray(object_xy)))
    return float(np.exp(-d / max(scale, 1e-6)))


def push_progress_reward(object_xy: np.ndarray, target_xy: np.ndarray,
                         prev_object_target_dist: float) -> float:
    """Reward for reducing the object->target distance this step (push only)."""
    d = float(np.linalg.norm(np.asarray(object_xy) - np.asarray(target_xy)))
    return float(prev_object_target_dist - d)
