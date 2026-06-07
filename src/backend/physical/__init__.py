"""Physical-fidelity layer for the G1 sim.

Post-hoc and in-loop checks that measure whether the *real* Unitree G1 could
execute what the sim shows — actuator saturation (PF-1), power/energy (PF-2),
thermal duty cycle (PF-3), stability/payload (PF-6), and the aggregate
feasibility verdict (PF-7). All real numbers come from ``g1_specs.py``.
"""
