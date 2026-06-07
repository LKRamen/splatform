# Manipulation honesty — base G1 has no hands (PF-8)

The whole point of the Physical-Fidelity phase is to **not** show the robot doing
things the real hardware cannot. The base Unitree G1 (and the 29-DOF model we
simulate) has 4–7-DOF arms but **no actuated fingers** — it physically cannot
grasp. The MJCF's `rubber_hand` geoms are fixed, non-articulated shells.

So every "manipulation" task must be one of two honest modes
(`src/backend/tasks/capabilities.py`):

| Mode | What it is | Hardware truth |
|------|------------|----------------|
| `PUSH` | Move an object with arm/body contact along the ground. No lift, no grasp. | What the **base G1** can actually do. |
| `CARRY_DEX_HAND` | Lift/carry an object. | Only with an **assumed Dex3/Dex5 hand add-on**; payload capped at ~2 kg and labeled "assumes Dex5 hand". |

## Task framings

| Task | Mode | Honest description |
|------|------|--------------------|
| `box_sort` | PUSH | Push colored boxes to matching floor zones with arm/body contact — no grasp. |
| `table_setup` | PUSH | Push objects to marked target positions — no grasp. |
| `package_delivery` | CARRY_DEX_HAND | Carry a ≤2 kg package A→B; **assumes a Dex5 hand**, mass-capped, UI-labeled. |

## Rules for building the Phase 8 task envs

1. Default to `PUSH`. Reward = reach (effector→object) + push progress
   (object→target). **No grasp-stability term** for push tasks.
2. Only use `CARRY_DEX_HAND` when the task explicitly sets `assumes_dex_hand`,
   and then cap object mass at `g1_specs.DEX_HAND_PAYLOAD_KG` and label it
   "assumes Dex5 hand" in the task intro overlay (Phase 9.1).
3. The Real World Context panel (Phase 9.3) must distinguish what the **base G1**
   can do (push) from what needs a **hand add-on** (grasp/carry) — copy is in
   `TASK_CAPABILITIES[...].real_world_context`.
4. `validate_object_mass(task_id, mass)` gates any object mass against the task's
   capability before a task spawns it.

This keeps the demo credible: the feasibility badge (PF-7) and these framings
together answer "could the real G1 do this?" without faking the hardware.
