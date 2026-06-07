import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

// ------------------------------------------------------------------
// Scene setup
// ------------------------------------------------------------------
const viewport = document.getElementById('viewport');
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.shadowMap.enabled = true;
renderer.outputColorSpace = THREE.SRGBColorSpace;
viewport.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x050508);
scene.fog = new THREE.Fog(0x050508, 30, 80);

const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 200);
camera.position.set(0, 5, 8);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.maxPolarAngle = Math.PI / 2 - 0.02;

// ------------------------------------------------------------------
// Lighting
// ------------------------------------------------------------------
scene.add(new THREE.AmbientLight(0x334466, 1.5));
const sun = new THREE.DirectionalLight(0xffffff, 2);
sun.position.set(10, 20, 10);
sun.castShadow = true;
scene.add(sun);
const fill = new THREE.DirectionalLight(0x4488ff, 0.5);
fill.position.set(-10, 5, -10);
scene.add(fill);

// ------------------------------------------------------------------
// Environment — procedural indoor lobby fallback (atrium, not a void)
// ------------------------------------------------------------------
const ROOM_HALF = 12;   // walls sit at x = ±12 and z = ±12
const ROOM_H = 4.5;     // ceiling height

/**
 * Build one wall as a group: a dark panel plus 2–3 tall emissive-blue
 * window openings. Local +Z is the inward-facing normal.
 * @param {THREE.Material} wallMat
 * @param {THREE.Material} windowMat
 * @returns {THREE.Group}
 */
function makeWall(wallMat, windowMat) {
  const g = new THREE.Group();
  const wall = new THREE.Mesh(new THREE.PlaneGeometry(ROOM_HALF * 2, ROOM_H), wallMat);
  wall.position.y = ROOM_H / 2;
  g.add(wall);
  for (const wx of [-6, 0, 6]) {
    const win = new THREE.Mesh(new THREE.PlaneGeometry(1.3, 2.6), windowMat);
    win.position.set(wx, 2.3, 0.03); // slightly inset toward the interior
    g.add(win);
  }
  return g;
}

/**
 * Materials shared across the lobby. Grouped so buildLobby() stays focused
 * on layout rather than material setup.
 * @returns {Record<string, THREE.Material>}
 */
function lobbyMaterials() {
  return {
    floor: new THREE.MeshStandardMaterial({ color: 0x1a1a2e, roughness: 0.9 }),
    ceil: new THREE.MeshStandardMaterial({ color: 0x14141f, roughness: 0.95, side: THREE.DoubleSide }),
    wall: new THREE.MeshStandardMaterial({ color: 0x16162a, roughness: 0.9, side: THREE.DoubleSide }),
    col: new THREE.MeshStandardMaterial({ color: 0x2a2a40, roughness: 0.7 }),
    window: new THREE.MeshStandardMaterial({ color: 0x16244a, emissive: 0x2a4d8f, emissiveIntensity: 0.6 }),
    panel: new THREE.MeshStandardMaterial({ color: 0x222018, emissive: 0xffe9c4, emissiveIntensity: 0.5 }),
  };
}

/**
 * Add the four structural columns at (±8, 0, ±8).
 * @param {THREE.Group} lobby
 * @param {THREE.Material} colMat
 */
function addColumns(lobby, colMat) {
  for (const cx of [-8, 8]) {
    for (const cz of [-8, 8]) {
      const col = new THREE.Mesh(new THREE.BoxGeometry(0.4, ROOM_H, 0.4), colMat);
      col.position.set(cx, ROOM_H / 2, cz);
      col.castShadow = true;
      lobby.add(col);
    }
  }
}

/**
 * Add three warm emissive ceiling panels, each with a soft fill light.
 * @param {THREE.Group} lobby
 * @param {THREE.Material} panelMat
 */
function addCeilingPanels(lobby, panelMat) {
  for (const px of [-6, 0, 6]) {
    const panel = new THREE.Mesh(new THREE.PlaneGeometry(2.5, 1.2), panelMat);
    panel.rotation.x = Math.PI / 2;
    panel.position.set(px, ROOM_H - 0.02, 0);
    lobby.add(panel);
    const glow = new THREE.PointLight(0xffe9c4, 6, 14, 2);
    glow.position.set(px, ROOM_H - 0.4, 0);
    lobby.add(glow);
  }
}

/**
 * Build a coherent indoor atrium: floor, ceiling, four walls with window
 * openings, structural columns, and warm emissive ceiling panels.
 * Returned as a single group so it can be hidden when a splat loads.
 * @returns {THREE.Group}
 */
function buildLobby() {
  const lobby = new THREE.Group();
  const mats = lobbyMaterials();
  const span = ROOM_HALF * 2;

  // Floor + grid (keep the dark grid look)
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(span, span), mats.floor);
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  lobby.add(floor, new THREE.GridHelper(span, span, 0x223344, 0x1a2233));

  // Ceiling + subtle grid
  const ceil = new THREE.Mesh(new THREE.PlaneGeometry(span, span), mats.ceil);
  ceil.rotation.x = Math.PI / 2;
  ceil.position.y = ROOM_H;
  const ceilGrid = new THREE.GridHelper(span, 12, 0x223344, 0x1a2233);
  ceilGrid.position.y = ROOM_H - 0.01;
  lobby.add(ceil, ceilGrid);

  // Four walls, oriented so the window faces point inward
  const wallPlacements = [
    { pos: [0, 0, -ROOM_HALF], rotY: 0 },
    { pos: [0, 0, ROOM_HALF], rotY: Math.PI },
    { pos: [-ROOM_HALF, 0, 0], rotY: Math.PI / 2 },
    { pos: [ROOM_HALF, 0, 0], rotY: -Math.PI / 2 },
  ];
  for (const { pos, rotY } of wallPlacements) {
    const wall = makeWall(mats.wall, mats.window);
    wall.position.set(pos[0], pos[1], pos[2]);
    wall.rotation.y = rotY;
    lobby.add(wall);
  }

  addColumns(lobby, mats.col);
  addCeilingPanels(lobby, mats.panel);
  return lobby;
}

// Preserved for reference — superseded by buildLobby().
function buildProceduralScene_old() {
  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(60, 60),
    new THREE.MeshLambertMaterial({ color: 0x1a1a2e })
  );
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);
  scene.add(new THREE.GridHelper(60, 60, 0x223344, 0x1a2233));
  const buildingMat = new THREE.MeshLambertMaterial({ color: 0x1e2040 });
  const buildingDefs = [
    [8, 12, 3, 20, 8], [-8, 10, -5, 18, 6], [15, 8, 10, 16, 5],
    [-15, 14, 8, 22, 10], [0, 6, -18, 12, 4], [20, 10, -8, 20, 7],
  ];
  for (const [x, h, z, d, w] of buildingDefs) {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), buildingMat);
    mesh.position.set(x, h / 2, z);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    scene.add(mesh);
  }
}

const lobbyGroup = buildLobby();
scene.add(lobbyGroup);

// ------------------------------------------------------------------
// Gaussian splat loading pipeline (@mkkellogg/gaussian-splats-3d)
// ------------------------------------------------------------------
const SPLAT_URL = '/assets/scene.splat';
const SPLAT_MODULE_URL =
  'https://cdn.jsdelivr.net/npm/@mkkellogg/gaussian-splats-3d@0.4.1/build/gaussian-splats-3d.module.js';

const splatOverlay = document.getElementById('splat-overlay');
const splatPct = document.getElementById('splat-pct');
const sceneIndicator = document.getElementById('scene-indicator');

/**
 * Update the status-bar scene indicator.
 * @param {boolean} isSplat true → live splat, false → procedural fallback
 */
function setSceneIndicator(isSplat) {
  if (!sceneIndicator) return;
  sceneIndicator.textContent = isSplat ? '● Live Splat' : '● Procedural';
  sceneIndicator.style.color = isSplat ? 'var(--teal)' : 'var(--muted)';
}

// Default to procedural until/unless a splat successfully loads.
setSceneIndicator(false);

// ------------------------------------------------------------------
// Splat alignment. Reconstructions rarely arrive in Three.js's Y-up frame,
// so the loaded cloud usually needs a rotation/scale/offset to line up with
// the robot and floor. These are the knobs to tune against the real capture.
//
// Live-tune from the browser console, e.g.:
//   splatTransform.setRotation(-90, 0, 0)   // XYZ Euler degrees
//   splatTransform.setScale(1.5)
//   splatTransform.setPosition(0, -1.2, 0)
//   splatTransform.get()                    // read current values to bake in
// Once it lines up, copy splatTransform.get() back into SPLAT_ALIGNMENT below.
// ------------------------------------------------------------------
const SPLAT_ALIGNMENT = {
  position: [0, 0, 0],
  rotationDeg: [0, 0, 0], // XYZ Euler degrees
  scale: 1,
};

let _splatGroup = null;

function applySplatTransform() {
  if (!_splatGroup) return;
  const a = SPLAT_ALIGNMENT;
  _splatGroup.position.set(a.position[0], a.position[1], a.position[2]);
  _splatGroup.quaternion.setFromEuler(new THREE.Euler(
    THREE.MathUtils.degToRad(a.rotationDeg[0]),
    THREE.MathUtils.degToRad(a.rotationDeg[1]),
    THREE.MathUtils.degToRad(a.rotationDeg[2]),
    'XYZ',
  ));
  _splatGroup.scale.setScalar(a.scale);
}

// Expose live tuning hooks for configuring alignment against the real splat.
window.splatTransform = {
  setRotation(x, y, z) { SPLAT_ALIGNMENT.rotationDeg = [x, y, z]; applySplatTransform(); },
  setPosition(x, y, z) { SPLAT_ALIGNMENT.position = [x, y, z]; applySplatTransform(); },
  setScale(s) { SPLAT_ALIGNMENT.scale = s; applySplatTransform(); },
  get() { return JSON.parse(JSON.stringify(SPLAT_ALIGNMENT)); },
};

async function tryLoadSplat() {
  try {
    // Skip the (heavy) library import entirely if the file isn't present.
    const head = await fetch(SPLAT_URL, { method: 'HEAD' });
    if (!head.ok) throw new Error('scene.splat not found');

    const GaussianSplats3D = await import(SPLAT_MODULE_URL);
    if (!GaussianSplats3D || !GaussianSplats3D.DropInViewer) {
      throw new Error('gaussian-splats-3d module unavailable');
    }

    splatOverlay.classList.remove('hidden');
    if (splatPct) splatPct.textContent = '0%';

    const dropIn = new GaussianSplats3D.DropInViewer({ gpuAcceleratedSort: false });
    await dropIn.addSplatScene(SPLAT_URL, {
      splatAlphaRemovalThreshold: 5,
      showLoadingUI: false,
      onProgress: (percent) => {
        if (splatPct) splatPct.textContent = `${Math.round(percent)}%`;
      },
    });

    scene.add(dropIn);
    _splatGroup = dropIn;
    applySplatTransform(); // align the cloud to the robot/floor frame
    if (lobbyGroup) lobbyGroup.visible = false; // splat replaces the lobby
    splatOverlay.classList.add('hidden');
    setSceneIndicator(true);
    console.log('Splat loaded successfully — tune alignment via splatTransform.setRotation/Position/Scale');
  } catch {
    splatOverlay.classList.add('hidden');
    if (lobbyGroup) lobbyGroup.visible = true;
    setSceneIndicator(false);
    console.log('Splat not found, using procedural fallback');
  }
}
tryLoadSplat();

// ------------------------------------------------------------------
// Robot — load GLB if it has a real skeleton, else build a clean
// procedural humanoid rig from primitives.
// ------------------------------------------------------------------
let robotGroup = new THREE.Group();
scene.add(robotGroup);

// Joint order matches the MuJoCo Menagerie Unitree G1 actuators (29 DOF).
const JOINT_NAMES = [
  'left_hip_pitch', 'left_hip_roll', 'left_hip_yaw', 'left_knee', 'left_ankle_pitch', 'left_ankle_roll',
  'right_hip_pitch', 'right_hip_roll', 'right_hip_yaw', 'right_knee', 'right_ankle_pitch', 'right_ankle_roll',
  'waist_yaw', 'waist_roll', 'waist_pitch',
  'left_shoulder_pitch', 'left_shoulder_roll', 'left_shoulder_yaw', 'left_elbow',
  'left_wrist_roll', 'left_wrist_pitch', 'left_wrist_yaw',
  'right_shoulder_pitch', 'right_shoulder_roll', 'right_shoulder_yaw', 'right_elbow',
  'right_wrist_roll', 'right_wrist_pitch', 'right_wrist_yaw',
];

// Joint bone map (populated only when a skinned GLB loads).
const jointBones = {};

// applyJoints(joints) is set by whichever robot builder wins (GLB or
// procedural). It maps the 19 incoming angles onto rotation axes.
let applyJoints = () => {};

// ------------------------------------------------------------------
// Procedural Berkeley Humanoid Lite rig (~0.9 m, ~16 kg proportions).
//
// Visual target: the open-source Berkeley Humanoid Lite — a small 3D-printed
// humanoid built from light/white printed shells with dark structural joint
// housings, exposed cylindrical actuator "pucks" at the hips/shoulders/
// knees/elbows, blocky modular limb segments, flat chest/pelvis panels, and a
// compact rectangular sensor head.
// ------------------------------------------------------------------
// Retained name (was the old teal tint) so nothing outside this block breaks;
// the rig is now a printed-white shell with dark joints, not teal.
const ROBOT_TEAL = 0xeef0f2;        // off-white 3D-printed shell
const ROBOT_JOINT_DARK = 0x1b1d22;  // dark actuator housings / joint pucks
const ROBOT_ACCENT = 0x00e5cc;      // small teal accent (status LED feel)

/**
 * Shared materials for the printed humanoid. Built once and reused across all
 * segments so the rig stays a coherent white-shell / dark-joint scheme.
 * @returns {{ shell: THREE.Material, joint: THREE.Material, accent: THREE.Material }}
 */
function robotMaterials() {
  return {
    shell: new THREE.MeshStandardMaterial({
      color: ROBOT_TEAL, metalness: 0.05, roughness: 0.6,
    }),
    joint: new THREE.MeshStandardMaterial({
      color: ROBOT_JOINT_DARK, metalness: 0.55, roughness: 0.35,
    }),
    accent: new THREE.MeshStandardMaterial({
      color: ROBOT_ACCENT, emissive: ROBOT_ACCENT, emissiveIntensity: 0.6,
      metalness: 0.2, roughness: 0.4,
    }),
  };
}

/**
 * A dark cylindrical actuator "puck" — the exposed joint housing seen at the
 * hips, shoulders, knees, and elbows of the Berkeley Humanoid Lite. Oriented
 * with its axis along a chosen world-ish axis ('x', 'y', or 'z').
 * @param {number} radius
 * @param {number} length
 * @param {THREE.Material} jointMat
 * @param {'x'|'y'|'z'} axis cylinder axis (default 'x', sideways)
 * @returns {THREE.Mesh}
 */
function makeJointPuck(radius, length, jointMat, axis = 'x') {
  const puck = new THREE.Mesh(
    new THREE.CylinderGeometry(radius, radius, length, 16), jointMat);
  if (axis === 'x') puck.rotation.z = Math.PI / 2;
  else if (axis === 'z') puck.rotation.x = Math.PI / 2;
  puck.castShadow = true;
  return puck;
}

/**
 * Create a named pivot Object3D with a primitive shell mesh child offset so
 * the limb extends away from the pivot point. Optional extra detail meshes
 * (joint pucks, panels) are added at the pivot so they stay at the joint.
 * @param {string} name
 * @param {THREE.BufferGeometry} geometry shell geometry
 * @param {THREE.Material} material shell material
 * @param {[number, number, number]} meshOffset local offset of the shell mesh
 * @param {THREE.Object3D[]} [details] cosmetic child meshes added at the pivot
 * @returns {THREE.Object3D}
 */
function makeSegment(name, geometry, material, meshOffset, details = []) {
  const pivot = new THREE.Object3D();
  pivot.name = name;
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(meshOffset[0], meshOffset[1], meshOffset[2]);
  mesh.castShadow = true;
  pivot.add(mesh);
  for (const d of details) pivot.add(d);
  return pivot;
}

/**
 * Build one arm chain: upper_arm -> forearm -> hand, hanging downward from
 * the shoulder pivot. Blocky printed shells with a dark actuator puck at the
 * shoulder and elbow joints.
 * @param {'left'|'right'} side
 * @param {{ shell: THREE.Material, joint: THREE.Material, accent: THREE.Material }} mats
 * @returns {Record<string, THREE.Object3D>} segments keyed by name
 */
function buildArm(side, mats) {
  const sx = side === 'left' ? 1 : -1;

  // Upper arm: rounded box shell + dark shoulder puck at the pivot.
  const shoulderPuck = makeJointPuck(0.045, 0.07, mats.joint, 'x');
  const upper = makeSegment(`${side}_upper_arm`,
    new THREE.BoxGeometry(0.06, 0.18, 0.06), mats.shell, [0, -0.11, 0],
    [shoulderPuck]);
  upper.position.set(sx * 0.15, 0.34, 0);

  // Forearm: slimmer shell + dark elbow puck at the pivot.
  const elbowPuck = makeJointPuck(0.035, 0.055, mats.joint, 'x');
  const fore = makeSegment(`${side}_forearm`,
    new THREE.BoxGeometry(0.05, 0.16, 0.05), mats.shell, [0, -0.10, 0],
    [elbowPuck]);
  fore.position.set(0, -0.21, 0);
  upper.add(fore);

  // Hand: small dark gripper block.
  const hand = makeSegment(`${side}_hand`,
    new THREE.BoxGeometry(0.05, 0.08, 0.035), mats.joint, [0, -0.05, 0]);
  hand.position.set(0, -0.20, 0);
  fore.add(hand);

  return { [`${side}_upper_arm`]: upper, [`${side}_forearm`]: fore, [`${side}_hand`]: hand };
}

/**
 * Build one leg chain: thigh -> shin -> foot, hanging downward so the feet
 * reach the floor. Blocky printed shells with dark hip and knee pucks.
 * @param {'left'|'right'} side
 * @param {{ shell: THREE.Material, joint: THREE.Material, accent: THREE.Material }} mats
 * @returns {Record<string, THREE.Object3D>} segments keyed by name
 */
function buildLeg(side, mats) {
  const sx = side === 'left' ? 1 : -1;

  // Thigh: chunky printed shell + dark hip actuator puck at the pivot.
  const hipPuck = makeJointPuck(0.06, 0.085, mats.joint, 'x');
  const thigh = makeSegment(`${side}_thigh`,
    new THREE.BoxGeometry(0.085, 0.26, 0.09), mats.shell, [0, -0.16, 0],
    [hipPuck]);
  thigh.position.set(sx * 0.085, -0.02, 0);

  // Shin: tapered shell + dark knee puck at the pivot.
  const kneePuck = makeJointPuck(0.05, 0.07, mats.joint, 'x');
  const shin = makeSegment(`${side}_shin`,
    new THREE.BoxGeometry(0.07, 0.26, 0.075), mats.shell, [0, -0.16, 0],
    [kneePuck]);
  shin.position.set(0, -0.34, 0);
  thigh.add(shin);

  // Foot: flat dark sole that extends forward.
  const foot = makeSegment(`${side}_foot`,
    new THREE.BoxGeometry(0.085, 0.045, 0.20), mats.joint, [0, -0.022, 0.06]);
  foot.position.set(0, -0.34, 0);
  shin.add(foot);

  return { [`${side}_thigh`]: thigh, [`${side}_shin`]: shin, [`${side}_foot`]: foot };
}

/**
 * Build a Berkeley-Humanoid-Lite-styled humanoid: white printed shells with
 * dark modular joints, flat chest/pelvis panels, exposed actuator pucks, and a
 * compact rectangular sensor head. Keeps the exact named pivot hierarchy the
 * animation contract depends on.
 * @returns {{ root: THREE.Object3D, segments: Record<string, THREE.Object3D> }}
 */
function buildProceduralRobot() {
  const mats = robotMaterials();

  // Torso (root): pelvis block at the rig origin, chest shell above it.
  // Cosmetic children: a dark pelvis girdle and a chest sensor strip.
  const pelvis = new THREE.Mesh(new THREE.BoxGeometry(0.21, 0.08, 0.13), mats.joint);
  pelvis.position.set(0, 0.02, 0);
  pelvis.castShadow = true;

  const chestStrip = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.06, 0.005), mats.accent);
  chestStrip.position.set(0, 0.30, 0.085);

  const shoulderYoke = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.06, 0.09), mats.joint);
  shoulderYoke.position.set(0, 0.36, 0);
  shoulderYoke.castShadow = true;

  const torso = makeSegment('torso',
    new THREE.BoxGeometry(0.20, 0.30, 0.13), mats.shell, [0, 0.20, 0],
    [pelvis, chestStrip, shoulderYoke]);

  // Head: compact rectangular sensor head with a dark visor face.
  const visor = new THREE.Mesh(new THREE.BoxGeometry(0.10, 0.05, 0.01), mats.joint);
  visor.position.set(0, 0.0, 0.06);
  const head = makeSegment('head',
    new THREE.BoxGeometry(0.13, 0.11, 0.11), mats.shell, [0, 0, 0], [visor]);
  head.position.set(0, 0.46, 0);
  torso.add(head);

  const segments = { torso, head };
  for (const side of ['left', 'right']) {
    const arm = buildArm(side, mats);
    const leg = buildLeg(side, mats);
    Object.assign(segments, arm, leg);
    torso.add(arm[`${side}_upper_arm`], leg[`${side}_thigh`]);
  }
  return { root: torso, segments };
}

// Maps each of the 29 G1 joints (in JOINT_NAMES order) to a rig segment and
// the local rotation axis it drives: pitch=X, roll=Z, yaw=Y. Multiple joints
// land on one segment via distinct axes (e.g. the hip's pitch/roll/yaw).
const JOINT_TARGETS = [
  ['left_thigh', 'x'],   // left_hip_pitch
  ['left_thigh', 'z'],   // left_hip_roll
  ['left_thigh', 'y'],   // left_hip_yaw
  ['left_shin', 'x'],    // left_knee
  ['left_foot', 'x'],    // left_ankle_pitch
  ['left_foot', 'z'],    // left_ankle_roll
  ['right_thigh', 'x'],  // right_hip_pitch
  ['right_thigh', 'z'],  // right_hip_roll
  ['right_thigh', 'y'],  // right_hip_yaw
  ['right_shin', 'x'],   // right_knee
  ['right_foot', 'x'],   // right_ankle_pitch
  ['right_foot', 'z'],   // right_ankle_roll
  ['torso', 'y'],        // waist_yaw
  ['torso', 'z'],        // waist_roll
  ['torso', 'x'],        // waist_pitch
  ['left_upper_arm', 'x'],   // left_shoulder_pitch
  ['left_upper_arm', 'z'],   // left_shoulder_roll
  ['left_upper_arm', 'y'],   // left_shoulder_yaw
  ['left_forearm', 'x'],     // left_elbow
  ['left_hand', 'y'],        // left_wrist_roll
  ['left_hand', 'x'],        // left_wrist_pitch
  ['left_hand', 'z'],        // left_wrist_yaw
  ['right_upper_arm', 'x'],  // right_shoulder_pitch
  ['right_upper_arm', 'z'],  // right_shoulder_roll
  ['right_upper_arm', 'y'],  // right_shoulder_yaw
  ['right_forearm', 'x'],    // right_elbow
  ['right_hand', 'y'],       // right_wrist_roll
  ['right_hand', 'x'],       // right_wrist_pitch
  ['right_hand', 'z'],       // right_wrist_yaw
];

function installProceduralRobot() {
  const { root, segments } = buildProceduralRobot();
  robotGroup.add(root);
  applyJoints = (joints) => {
    for (let i = 0; i < JOINT_NAMES.length; i++) {
      const target = JOINT_TARGETS[i];
      const obj = segments[target[0]];
      if (obj) obj.rotation[target[1]] = joints[i] || 0;
    }
  };
  console.log('[robot] using procedural humanoid rig');
}

function installGlbRobot(gltf, bones) {
  robotGroup.add(gltf.scene);
  for (const bone of bones) {
    const name = bone.name.toLowerCase().replace(/_link$/, '');
    if (JOINT_NAMES.includes(name)) jointBones[name] = bone;
  }
  applyJoints = (joints) => {
    for (let i = 0; i < JOINT_NAMES.length; i++) {
      const bone = jointBones[JOINT_NAMES[i]];
      if (bone) bone.rotation.x = joints[i] || 0; // GLB revolute on X
    }
  };
  console.log('[robot] using GLB skeleton');
}

// Preserved for reference — superseded by buildProceduralRobot().
function buildCapsulePlaceholder_old() {
  const mat = new THREE.MeshLambertMaterial({ color: 0x00e5cc });
  const torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.18, 0.6, 4, 8), mat);
  torso.position.set(0, 1.0, 0);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.12, 8, 8), mat);
  head.position.set(0, 1.55, 0);
  for (const sx of [-1, 1]) {
    const arm = new THREE.Mesh(new THREE.CapsuleGeometry(0.05, 0.4, 4, 8), mat);
    arm.position.set(sx * 0.3, 0.9, 0);
    robotGroup.add(arm);
  }
  for (const sx of [-1, 1]) {
    const leg = new THREE.Mesh(new THREE.CapsuleGeometry(0.07, 0.5, 4, 8), mat);
    leg.position.set(sx * 0.12, 0.45, 0);
    robotGroup.add(leg);
  }
  robotGroup.add(torso, head);
}

const loader = new GLTFLoader();
loader.load(
  '/assets/g1.glb',
  (gltf) => {
    // Only trust the GLB if it carries a real skinned skeleton with bones.
    const bones = [];
    gltf.scene.traverse((obj) => {
      if (obj.isSkinnedMesh && obj.skeleton && obj.skeleton.bones.length > 0) {
        bones.push(...obj.skeleton.bones);
      }
    });
    if (bones.length > 0) {
      installGlbRobot(gltf, bones);
    } else {
      console.log('[robot] GLB has no valid skeleton — falling back to procedural rig');
      installProceduralRobot();
    }
  },
  undefined,
  () => {
    console.log('[robot] GLB failed to load — falling back to procedural rig');
    installProceduralRobot();
  }
);

// ------------------------------------------------------------------
// Dynamic obstacle pedestrians
// ------------------------------------------------------------------
const _obstaclePool = [];
const _obstacleMat = new THREE.MeshLambertMaterial({ color: 0xff4466, transparent: true, opacity: 0.85 });

function _getOrCreateObstacle(idx) {
  if (!_obstaclePool[idx]) {
    const group = new THREE.Group();
    // Body capsule
    const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.15, 0.9, 4, 8), _obstacleMat);
    body.position.y = 0.55;
    // Head
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.11, 8, 8), _obstacleMat);
    head.position.y = 1.25;
    group.add(body, head);
    scene.add(group);
    _obstaclePool[idx] = group;
  }
  return _obstaclePool[idx];
}

function updateObstacles(obstacleList) {
  obstacleList.forEach((pos, idx) => {
    const mesh = _getOrCreateObstacle(idx);
    mesh.position.set(pos[0], 0, pos[2]);
    mesh.visible = true;
  });
  // Hide extras
  for (let i = obstacleList.length; i < _obstaclePool.length; i++) {
    if (_obstaclePool[i]) _obstaclePool[i].visible = false;
  }
}

// ------------------------------------------------------------------
// Waypoint markers
// ------------------------------------------------------------------
const waypointMarkers = [];
const pathLine = (() => {
  const geo = new THREE.BufferGeometry();
  const mat = new THREE.LineBasicMaterial({ color: 0x4488ff, opacity: 0.6, transparent: true });
  const line = new THREE.Line(geo, mat);
  scene.add(line);
  return line;
})();

export function setWaypointMarkers(waypoints) {
  waypointMarkers.forEach(m => scene.remove(m));
  waypointMarkers.length = 0;
  const pts = [];
  for (const [x, z] of waypoints) {
    const geo = new THREE.CylinderGeometry(0.15, 0.15, 1.2, 12);
    const mat = new THREE.MeshBasicMaterial({ color: 0x00e5cc, transparent: true, opacity: 0.8 });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(x, 0.6, z);
    scene.add(mesh);
    waypointMarkers.push(mesh);
    pts.push(new THREE.Vector3(x, 0.1, z));
  }
  if (pts.length > 1) {
    pathLine.geometry.setFromPoints(pts);
  }
}

// ------------------------------------------------------------------
// WebSocket handling — exposed globally for controls.js
// ------------------------------------------------------------------
let ws = null;
let currentVersion = 'v3';
const robotHistory = [];

const _statusDot  = document.getElementById('status-dot');
const _statusText = document.getElementById('status-text');
const _statusStep = document.getElementById('status-step');
const _statusFps  = document.getElementById('status-fps');

export function connectWS(version) {
  if (ws) ws.close();
  currentVersion = version || currentVersion;
  ws = new WebSocket(`ws://localhost:8765/simulate/${currentVersion}`);
  ws.onopen  = () => { _statusDot.classList.add('connected'); _statusText.textContent = `Connected · ${currentVersion}`; };
  ws.onclose = () => { _statusDot.classList.remove('connected'); _statusText.textContent = 'Disconnected'; };
  ws.onerror = () => { _statusText.textContent = 'Connection error'; };
  ws.onmessage = (ev) => {
    const frame = JSON.parse(ev.data);
    handleFrame(frame);
  };
}

let _lastFrameTime = performance.now();
let _fpsSmooth = 0;

function handleFrame(frame) {
  const now = performance.now();
  const dt = (now - _lastFrameTime) / 1000;
  _lastFrameTime = now;
  _fpsSmooth = _fpsSmooth * 0.9 + (1 / dt) * 0.1;
  _statusStep.textContent = `step ${frame.step}`;
  _statusFps.textContent  = `${_fpsSmooth.toFixed(0)} fps`;

  // Update robot position & heading. MuJoCo is Z-up; the viewer is Y-up, so
  // remap mj(x, y, z) -> three(x, z, y) — putting the real pelvis height on
  // the vertical axis and the mj horizontal y onto three's z (consistent with
  // how obstacles and waypoints are placed).
  const [mjx, mjy, mjz] = frame.position;
  const wx = mjx, wy = mjz, wz = mjy;
  robotGroup.position.set(wx, wy, wz);
  // Rig forward is +Z; face the travel direction (mj heading yaw about up).
  robotGroup.rotation.y = Math.PI / 2 - frame.heading;

  // Drive the active robot rig (procedural or GLB) from the joint stream.
  if (frame.joints) applyJoints(frame.joints);

  // Follow camera, trailing the robot along its travel direction.
  const fwdX = Math.cos(frame.heading), fwdZ = Math.sin(frame.heading);
  const behind = new THREE.Vector3(wx - fwdX * 6, wy + 3, wz - fwdZ * 6);
  camera.position.lerp(behind, 0.04);
  controls.target.lerp(new THREE.Vector3(wx, wy + 1, wz), 0.08);

  // Update dynamic obstacle positions
  if (frame.obstacles) updateObstacles(frame.obstacles);

  // Dispatch for scoring.js
  window.dispatchEvent(new CustomEvent('wsframe', { detail: frame }));
}

// ------------------------------------------------------------------
// Raycasting for waypoint placement (floor plane y=0)
// ------------------------------------------------------------------
const _raycaster = new THREE.Raycaster();
const _floorPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
const _hitPt = new THREE.Vector3();

export function getFloorHitPoint(clientX, clientY) {
  const rect = renderer.domElement.getBoundingClientRect();
  const ndc = new THREE.Vector2(
    ((clientX - rect.left) / rect.width)  * 2 - 1,
    -((clientY - rect.top)  / rect.height) * 2 + 1
  );
  _raycaster.setFromCamera(ndc, camera);
  _raycaster.ray.intersectPlane(_floorPlane, _hitPt);
  return { x: _hitPt.x, z: _hitPt.z };
}

// ------------------------------------------------------------------
// Resize & render loop
// ------------------------------------------------------------------
function resize() {
  const w = viewport.clientWidth, h = viewport.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(viewport);
resize();

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}
animate();

// Auto-connect
connectWS('v3');

// Export for controls.js
export { scene, camera };
