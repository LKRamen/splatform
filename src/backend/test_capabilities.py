"""PF-8 test: manipulation capability honesty (no grasp on base G1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from src.backend import g1_specs
from src.backend.tasks import capabilities as cap

# --- base G1 cannot grasp ---
assert g1_specs.HAS_HANDS is False
assert g1_specs.ASSUMES_DEX5_HAND is False
assert cap.max_payload_kg(assumes_dex_hand=False) == 0.0, "no hand -> cannot lift"
assert cap.max_payload_kg(assumes_dex_hand=True) == g1_specs.DEX_HAND_PAYLOAD_KG

# --- push tasks are push-based, no dex hand ---
for tid in ("box_sort", "table_setup"):
    c = cap.get_capability(tid)
    assert c.mode == cap.ManipulationMode.PUSH
    assert c.assumes_dex_hand is False
    assert c.max_object_mass_kg is None  # push = no lift cap
    assert "no grasp" in c.description.lower()

# --- package_delivery opts into an assumed Dex5 hand, mass-capped ---
pd = cap.get_capability("package_delivery")
assert pd.mode == cap.ManipulationMode.CARRY_DEX_HAND
assert pd.assumes_dex_hand is True
assert pd.max_object_mass_kg == g1_specs.DEX_HAND_PAYLOAD_KG
assert "assumes a dex5 hand" in pd.description.lower()

# --- mass validation gates carry tasks, not push tasks ---
assert cap.validate_object_mass("box_sort", 50.0) is True       # push: any mass slides
assert cap.validate_object_mass("package_delivery", 1.5) is True
assert cap.validate_object_mass("package_delivery", 5.0) is False  # over Dex cap

# --- push reward helpers (reach + push, no grasp term) ---
near = cap.reach_object_reward(np.array([0.0, 0.0]), np.array([0.1, 0.0]))
far = cap.reach_object_reward(np.array([0.0, 0.0]), np.array([2.0, 0.0]))
assert near > far > 0
# pushing the object closer to target yields positive progress
prev = float(np.linalg.norm(np.array([1.0, 0.0]) - np.array([0.0, 0.0])))
prog = cap.push_progress_reward(np.array([0.5, 0.0]), np.array([0.0, 0.0]), prev)
assert prog > 0

# --- every task carries real-world context distinguishing base vs hand add-on ---
for tid, c in cap.TASK_CAPABILITIES.items():
    assert c.real_world_context and ("hand" in c.real_world_context.lower())

print("PASS — base G1 cannot grasp; box_sort/table_setup are push-based; "
      "package_delivery assumes a mass-capped Dex5 hand; mass gating + push "
      "rewards + real-world context all honest")
