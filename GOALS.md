# Goals

Status key: [ ] not started · [~] in progress · [x] complete · [!] blocked

Work top-to-bottom. Do not skip unless marked [!] blocked.
After completing any item mark it [x] and update PROGRESS.md immediately.

---

## Phase 1–6 — Complete
All original scaffold, training pipeline, WebSocket server, frontend shell,
asset pipeline, and integration work is done. See PROGRESS.md for details.

---

## Phase 7 — Visual Polish (fix before anything else)

- [x] **7.A** Fix robot mesh: replace broken h1.glb assembly with a clean
  procedural Three.js humanoid rig. Capsules and boxes parented correctly
  (torso → shoulders → upper arms → forearms, torso → hips → thighs →
  shins → feet). Wire all 19 joint angles from WS stream to correct
  Object3D rotation axes. Keep GLB attempt — fall back to procedural if
  skeleton invalid.

- [ ] **7.B** Fix viewport void: procedural fallback scene must render a
  full indoor lobby environment — ceiling, four walls with window cutouts,
  structural columns, interior point lights. No more black void above the
  floor grid.

- [ ] **7.C** Verify splat loading pipeline end-to-end: confirm
  `@mkkellogg/gaussian-splats-3d` attempts `assets/scene.splat`, shows
  progress overlay ("Loading Fordham splat... X%"), hides procedural scene
  on success, falls back cleanly on missing file. Add "Live Splat" vs
  "Procedural Fallback" indicator to status bar.

---

## Phase 8 — Manipulation Task System

- [ ] **8.1** Refactor `h1_env.py` into a base class `H1ManipulationEnv`.
  Extend observation space to 65-dim as defined in CLAUDE.md (adds
  right_hand_pos, left_hand_pos, object_pos, object_vel, object_to_target,
  task_phase). Add object bodies to the MuJoCo scene (start with 2 boxes).

- [ ] **8.2** Build `src/backend/tasks/box_sort.py`. Task: 2 colored boxes
  start at random positions, robot must push each to its matching colored
  floor zone. Reward: distance of each box to its zone, bonus on completion.
  Registers as task id `"box_sort"`.

- [ ] **8.3** Build `src/backend/tasks/table_setup.py`. Task: 3 objects
  (chair, cup, folder — represented as differently-sized boxes) start
  scattered, robot must place them at marked target positions. Mirrors
  real hackathon setup work. Registers as task id `"table_setup"`.

- [ ] **8.4** Build `src/backend/tasks/package_delivery.py`. Task: robot
  picks up a box from a marked pickup zone, carries it to a drop zone 5m
  away without dropping it. Reward includes grasp stability (contact force
  continuity) and drop penalty. Registers as task id `"package_delivery"`.

- [ ] **8.5** Update `server.py` to accept task selection:
  `WS /simulate/{checkpoint}/{task_id}`. Load the correct task env.
  Include `"objects"` array in every WS frame as defined in CLAUDE.md.

- [ ] **8.6** Build `src/frontend/tasks.js`. Task selector dropdown (box
  sort / table setup / package delivery). When task changes, reconnect WS
  with new task_id. Render task objects in Three.js: colored boxes with
  matching colored target zones (glowing floor decals). Object meshes
  update position/rotation from WS stream every frame.

- [ ] **8.7** Update `rewards.py` with manipulation reward functions:
  `reach_object_reward`, `manipulation_reward`, `grasp_stability_reward`,
  `drop_penalty`. Update scoring rubric display in `scoring.js` to show
  new 4-dimension breakdown (task completion, manipulation precision, gait
  stability, energy).

---

## Phase 9 — Demo Polish

- [ ] **9.1** Add task intro overlay: when a new task starts, show a 2-second
  overlay naming the task and objective ("Task: Table Setup — place all
  objects at marked positions"). Auto-dismisses.

- [ ] **9.2** Update the comparison view (compare.html) to show the same
  task running on v1 vs v3 side by side. Object state must sync across
  both viewports from their respective WS streams.

- [ ] **9.3** Add a "Real World Context" panel to the sidebar. Three bullet
  points connecting each task to a real industry use case: box sort →
  Amazon warehouse, table setup → office service robots, package delivery
  → last-mile humanoid delivery. One sentence each, no fluff.

- [ ] **9.4** Demo script: write `DEMO.md` — a 3-minute spoken walkthrough
  for judges. Covers: what the splat is and why it matters, what task the
  robot is attempting, how checkpoints show learning, what real companies
  are doing the same thing at scale.

---

## Phase 10 — Stretch

- [ ] **10.1** Add obstacle course task: robot must step over a low barrier
  (0.2m high box geom) and squeeze through a 0.9m gap between two wall
  geoms to reach the goal. Tests locomotion + spatial awareness together.

- [ ] **10.2** Add live object placement: user can click in the 3D viewport
  to place a box at that position, server receives it via POST, MuJoCo
  scene updates, robot responds. Makes the demo interactive for judges.

- [ ] **10.3** Record a 60-second screen capture of the best policy
  completing table_setup in the Fordham splat. Embed as a fallback video
  in index.html in case the live server is down during judging.
