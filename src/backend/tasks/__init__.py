"""Manipulation task package.

Phase 8 task envs (box_sort, table_setup, package_delivery) are not built yet.
PF-8 lands the *honesty framework* they must follow: the base Unitree G1 has no
actuated fingers (g1_specs.HAS_HANDS=False) and therefore cannot grasp. Tasks
are PUSH-based by default; carrying requires explicitly assuming a dexterous-hand
add-on (Dex3/Dex5, <=2 kg). See ``capabilities`` for the model and registry.
"""
