"""
Merge all Unitree H1 STL meshes into a single GLB.
Usage: python src/backend/build_glb.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
import trimesh
import mujoco

MENAGERIE = os.path.join(os.path.dirname(__file__), '../../mujoco_menagerie/unitree_h1')
ASSETS    = os.path.join(MENAGERIE, 'assets')
OUT_GLB   = os.path.join(os.path.dirname(__file__), '../../assets/h1.glb')

def main():
    model = mujoco.MjModel.from_xml_path(os.path.join(MENAGERIE, 'h1.xml'))
    data  = mujoco.MjData(model)
    if model.nkey > 0:
        mujoco.mj_resetDataKeyframe(model, data, 0)
    mujoco.mj_forward(model, data)

    meshes = []
    colors = [
        [0.3, 0.3, 0.35, 1.0],   # dark grey for most links
        [0.15, 0.15, 0.2, 1.0],  # darker for joints
    ]

    for body_id in range(1, model.nbody):
        body_name = model.body(body_id).name
        # Get world position/rotation of this body
        xpos  = data.xpos[body_id].copy()
        xmat  = data.xmat[body_id].reshape(3, 3).copy()

        # Find geoms attached to this body
        for geom_id in range(model.ngeom):
            geom = model.geom(geom_id)
            if geom.bodyid != body_id:
                continue
            if geom.type != mujoco.mjtGeom.mjGEOM_MESH:
                continue

            mesh_id = int(geom.dataid[0]) if hasattr(geom.dataid, '__len__') else int(geom.dataid)
            if mesh_id < 0:
                continue

            mesh_name = model.mesh(mesh_id).name
            stl_path  = os.path.join(ASSETS, f'{mesh_name}.stl')
            if not os.path.exists(stl_path):
                print(f'  skip (no stl): {stl_path}')
                continue

            m = trimesh.load(stl_path, force='mesh')

            # Apply geom local pose (relative to body)
            geom_pos  = geom.pos.copy()
            geom_quat = geom.quat.copy()  # w,x,y,z
            # Convert quaternion to rotation matrix
            w,x,y,z = geom_quat
            R_geom = np.array([
                [1-2*(y*y+z*z), 2*(x*y-w*z),   2*(x*z+w*y)],
                [2*(x*y+w*z),   1-2*(x*x+z*z), 2*(y*z-w*x)],
                [2*(x*z-w*y),   2*(y*z+w*x),   1-2*(x*x+y*y)],
            ])
            T_geom = np.eye(4)
            T_geom[:3,:3] = R_geom
            T_geom[:3, 3] = geom_pos

            # Body world transform
            T_body = np.eye(4)
            T_body[:3,:3] = xmat
            T_body[:3, 3] = xpos

            T_world = T_body @ T_geom
            m.apply_transform(T_world)

            # Colour by vertical position for visual variety
            col = [0.25, 0.27, 0.32, 1.0] if xpos[2] > 0.8 else [0.18, 0.18, 0.22, 1.0]
            m.visual = trimesh.visual.ColorVisuals(mesh=m, face_colors=col)
            meshes.append(m)
            print(f'  added: {mesh_name} @ {xpos.round(3)}')

    if not meshes:
        print('No meshes found — creating capsule placeholder')
        meshes = [trimesh.creation.capsule(radius=0.18, height=0.8)]

    combined = trimesh.util.concatenate(meshes)
    os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
    combined.export(OUT_GLB)
    print(f'\nExported {len(meshes)} meshes → {OUT_GLB}')
    print(f'Vertices: {len(combined.vertices):,}  Faces: {len(combined.faces):,}')


if __name__ == '__main__':
    main()
