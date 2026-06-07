# Claude Prompts — Visual Fix Tasks

Run these in order. Prompt 1 first, then Prompt 2.
They touch different files and will not conflict.

---

## PROMPT 1 — Fix the Robot Mesh

Paste this exactly into Claude:

```
Read CLAUDE.md, GOALS.md, and PROGRESS.md before starting.
This is goal 7.A.

The robot mesh in the frontend renders as disconnected floating body part
chunks. The h1.glb was assembled from individual STL pieces with no skeleton
hierarchy or parent-child transforms, so joints cannot animate and parts
float at wrong positions.

Fix this in src/frontend/viewer.js:

1. Write a buildProceduralRobot() function that constructs a clean Three.js
   humanoid from CapsuleGeometry and BoxGeometry primitives. H1 proportions:
   1.8m tall, 47kg. Segment hierarchy must be:
     torso (root)
     ├── head
     ├── left_upper_arm → left_forearm → left_hand
     ├── right_upper_arm → right_forearm → right_hand
     ├── left_thigh → left_shin → left_foot
     └── right_thigh → right_shin → right_foot
   Each segment is a named THREE.Object3D with a mesh child. Color the
   robot teal (#00e5cc) so it reads clearly against the dark scene.

2. Map the 19 incoming joint angles from the WebSocket stream to the correct
   Object3D rotation axes on this rig. Joint order from CLAUDE.md:
   left_hip_yaw, left_hip_roll, left_hip_pitch, left_knee, left_ankle,
   right_hip_yaw, right_hip_roll, right_hip_pitch, right_knee, right_ankle,
   torso, left_shoulder_pitch, left_shoulder_roll, left_elbow,
   right_shoulder_pitch, right_shoulder_roll, right_elbow,
   left_wrist_roll, right_wrist_roll

3. Keep the existing GLTFLoader attempt for h1.glb. If the loaded GLB has a
   valid SkinnedMesh with bones, use it. If not, call buildProceduralRobot()
   as the fallback. Log which path was taken to the browser console.

4. The robot must visibly animate — limbs should move — when joint data
   streams in over WebSocket. Test by confirming leg joints rotate during
   the simulation.

Mark 7.A complete in GOALS.md and update PROGRESS.md when done.
```

---

## PROMPT 2 — Fix the Black Void + Verify Splat Loading

Paste this exactly into Claude after Prompt 1 is complete:

```
Read CLAUDE.md, GOALS.md, and PROGRESS.md before starting.
This covers goals 7.B and 7.C.

There are two problems to fix in src/frontend/viewer.js:

--- PROBLEM 1: Black void in viewport (goal 7.B) ---

The procedural fallback scene only has a floor grid. Everything above it
is black void. Replace the procedural scene with a full indoor lobby:

- Floor: existing dark grid, keep it
- Ceiling: flat plane at y=4.5m, same dark material as floor with subtle grid
- Four walls: at x=±12 and z=±12, height 4.5m. Each wall gets 2-3 tall
  rectangular cutouts (window openings) with a faint emissive blue tint
  to suggest exterior light
- Four columns: at (±8, 0, ±8), 0.4m square, full ceiling height,
  slightly lighter material than walls
- Lighting: 3 rectangular emissive panels on the ceiling (warm white,
  low intensity), plus the existing ambient/directional lights
- The result should feel like an indoor atrium, not a void. Dark, moody,
  but spatially coherent.

--- PROBLEM 2: Splat loading pipeline (goal 7.C) ---

Audit and fix the Gaussian splat loading in viewer.js:

1. Confirm the loader attempts assets/scene.splat using
   @mkkellogg/gaussian-splats-3d. If the import or loader is broken, fix it.

2. While loading, show a text overlay in the center of the viewport:
   "Loading Fordham splat... X%" where X updates from 0 to 100 as the
   splat streams in. Use the library's onProgress callback.

3. On successful load: hide the procedural lobby geometry entirely
   (set visible=false on the lobby group). Show the splat. Log
   "Splat loaded successfully" to console.

4. On load failure or missing file: keep the procedural lobby visible.
   Log "Splat not found, using procedural fallback" to console.

5. In the bottom status bar, add a scene indicator next to the connection
   status dot: show "● Live Splat" in teal or "● Procedural" in gray
   depending on which scene is active.

Mark 7.B and 7.C complete in GOALS.md and update PROGRESS.md when done.
```
