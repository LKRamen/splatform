import mujoco
import os

xml_path = os.path.join(os.path.dirname(__file__), '../../mujoco_menagerie/unitree_h1/h1.xml')
model = mujoco.MjModel.from_xml_path(xml_path)

print(f'nq (positions): {model.nq}')
print(f'nv (velocities): {model.nv}')
print(f'nu (actuators): {model.nu}')
print('Actuator names:')
for i in range(model.nu):
    print(f'  [{i}] {model.actuator(i).name}')
