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
// Floor / environment — procedural NYC-style fallback
// ------------------------------------------------------------------
function buildProceduralScene() {
  // Ground
  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(60, 60),
    new THREE.MeshLambertMaterial({ color: 0x1a1a2e })
  );
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);

  // Grid overlay
  const grid = new THREE.GridHelper(60, 60, 0x223344, 0x1a2233);
  scene.add(grid);

  // Buildings
  const buildingMat = new THREE.MeshLambertMaterial({ color: 0x1e2040 });
  const buildingDefs = [
    [8, 12, 3, 20, 8],
    [-8, 10, -5, 18, 6],
    [15, 8, 10, 16, 5],
    [-15, 14, 8, 22, 10],
    [0, 6, -18, 12, 4],
    [20, 10, -8, 20, 7],
  ];
  for (const [x, h, z, d, w] of buildingDefs) {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), buildingMat);
    mesh.position.set(x, h / 2, z);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    scene.add(mesh);
  }

  // Sidewalk strips
  const swMat = new THREE.MeshLambertMaterial({ color: 0x22223a });
  for (let i = -2; i <= 2; i++) {
    const sw = new THREE.Mesh(new THREE.PlaneGeometry(0.4, 60), swMat);
    sw.rotation.x = -Math.PI / 2;
    sw.position.set(i * 2, 0.01, 0);
    scene.add(sw);
  }
}

buildProceduralScene();

// Try loading real splat — if available
const splatOverlay = document.getElementById('splat-overlay');
const splatPct = document.getElementById('splat-pct');

async function tryLoadSplat() {
  try {
    const { GaussianSplatMesh } = await import(
      'https://cdn.jsdelivr.net/npm/@mkkellogg/gaussian-splats-3d@0.4.1/build/gaussian-splats-3d.module.js'
    ).catch(() => null);
    if (!GaussianSplatMesh) { splatOverlay.classList.add('hidden'); return; }

    const resp = await fetch('/assets/scene.splat', { method: 'HEAD' });
    if (!resp.ok) { splatOverlay.classList.add('hidden'); return; }

    splatOverlay.classList.remove('hidden');
    const viewer = new GaussianSplatMesh(renderer, camera, scene);
    await viewer.loadFile('/assets/scene.splat', {
      onProgress: (pct) => { splatPct.textContent = `${Math.round(pct * 100)}%`; }
    });
    splatOverlay.classList.add('hidden');
  } catch {
    splatOverlay.classList.add('hidden');
  }
}
tryLoadSplat();

// ------------------------------------------------------------------
// Robot — load GLB if it has a real skeleton, else build a clean
// procedural humanoid rig from primitives.
// ------------------------------------------------------------------
let robotGroup = new THREE.Group();
scene.add(robotGroup);

// Joint order is locked by CLAUDE.md (matches MuJoCo Menagerie H1 actuators).
const JOINT_NAMES = [
  'left_hip_yaw', 'left_hip_roll', 'left_hip_pitch', 'left_knee', 'left_ankle',
  'right_hip_yaw', 'right_hip_roll', 'right_hip_pitch', 'right_knee', 'right_ankle',
  'torso',
  'left_shoulder_pitch', 'left_shoulder_roll', 'left_elbow',
  'right_shoulder_pitch', 'right_shoulder_roll', 'right_elbow',
  'left_wrist_roll', 'right_wrist_roll',
];

// Joint bone map (populated only when a skinned GLB loads).
const jointBones = {};

// applyJoints(joints) is set by whichever robot builder wins (GLB or
// procedural). It maps the 19 incoming angles onto rotation axes.
let applyJoints = () => {};

// ------------------------------------------------------------------
// Procedural H1 rig (1.8 m, 47 kg proportions)
// ------------------------------------------------------------------
const ROBOT_TEAL = 0x00e5cc;

/**
 * Create a named pivot Object3D with a primitive mesh child offset so the
 * limb extends away from the pivot point.
 * @param {string} name
 * @param {THREE.BufferGeometry} geometry
 * @param {THREE.Material} material
 * @param {[number, number, number]} meshOffset local offset of the mesh
 * @returns {THREE.Object3D}
 */
function makeSegment(name, geometry, material, meshOffset) {
  const pivot = new THREE.Object3D();
  pivot.name = name;
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(meshOffset[0], meshOffset[1], meshOffset[2]);
  mesh.castShadow = true;
  pivot.add(mesh);
  return pivot;
}

/**
 * Build one arm chain: upper_arm -> forearm -> hand, hanging downward from
 * the shoulder pivot so rotations read naturally.
 * @param {'left'|'right'} side
 * @param {THREE.Material} material
 * @returns {Record<string, THREE.Object3D>} segments keyed by name
 */
function buildArm(side, material) {
  const sx = side === 'left' ? 1 : -1;
  const upper = makeSegment(`${side}_upper_arm`,
    new THREE.CapsuleGeometry(0.05, 0.22, 4, 10), material, [0, -0.14, 0]);
  upper.position.set(sx * 0.20, 0.56, 0);

  const fore = makeSegment(`${side}_forearm`,
    new THREE.CapsuleGeometry(0.045, 0.20, 4, 10), material, [0, -0.13, 0]);
  fore.position.set(0, -0.28, 0);
  upper.add(fore);

  const hand = makeSegment(`${side}_hand`,
    new THREE.BoxGeometry(0.08, 0.1, 0.05), material, [0, -0.06, 0]);
  hand.position.set(0, -0.26, 0);
  fore.add(hand);

  return { [`${side}_upper_arm`]: upper, [`${side}_forearm`]: fore, [`${side}_hand`]: hand };
}

/**
 * Build one leg chain: thigh -> shin -> foot, hanging downward so the feet
 * reach the floor when the rig root sits at pelvis height.
 * @param {'left'|'right'} side
 * @param {THREE.Material} material
 * @returns {Record<string, THREE.Object3D>} segments keyed by name
 */
function buildLeg(side, material) {
  const sx = side === 'left' ? 1 : -1;
  const thigh = makeSegment(`${side}_thigh`,
    new THREE.CapsuleGeometry(0.08, 0.30, 4, 10), material, [0, -0.22, 0]);
  thigh.position.set(sx * 0.10, 0, 0);

  const shin = makeSegment(`${side}_shin`,
    new THREE.CapsuleGeometry(0.07, 0.30, 4, 10), material, [0, -0.22, 0]);
  shin.position.set(0, -0.44, 0);
  thigh.add(shin);

  const foot = makeSegment(`${side}_foot`,
    new THREE.BoxGeometry(0.10, 0.06, 0.24), material, [0, -0.03, 0.07]);
  foot.position.set(0, -0.44, 0);
  shin.add(foot);

  return { [`${side}_thigh`]: thigh, [`${side}_shin`]: shin, [`${side}_foot`]: foot };
}

/**
 * Build a clean teal humanoid from capsules and boxes with a correct
 * parent-child hierarchy so every joint animates its descendants.
 * @returns {{ root: THREE.Object3D, segments: Record<string, THREE.Object3D> }}
 */
function buildProceduralRobot() {
  const bodyMat = new THREE.MeshStandardMaterial({
    color: ROBOT_TEAL, metalness: 0.35, roughness: 0.5,
  });

  // Torso (root): pelvis at the rig origin, body extends upward.
  const torso = makeSegment('torso',
    new THREE.CapsuleGeometry(0.16, 0.42, 6, 12), bodyMat, [0, 0.34, 0]);
  const head = makeSegment('head',
    new THREE.SphereGeometry(0.13, 16, 16), bodyMat, [0, 0, 0]);
  head.position.set(0, 0.72, 0);
  torso.add(head);

  const segments = { torso, head };
  for (const side of ['left', 'right']) {
    const arm = buildArm(side, bodyMat);
    const leg = buildLeg(side, bodyMat);
    Object.assign(segments, arm, leg);
    torso.add(arm[`${side}_upper_arm`], leg[`${side}_thigh`]);
  }
  return { root: torso, segments };
}

// Maps each of the 19 joints (in JOINT_NAMES order) to a rig segment and the
// local rotation axis it drives: hip yaw=Y / roll=Z / pitch=X,
// knee/ankle/elbow = pitch(X), shoulder pitch=X / roll=Z, wrist = roll(Y),
// torso = yaw(Y).
const JOINT_TARGETS = [
  ['left_thigh', 'y'],   // left_hip_yaw
  ['left_thigh', 'z'],   // left_hip_roll
  ['left_thigh', 'x'],   // left_hip_pitch
  ['left_shin', 'x'],    // left_knee
  ['left_foot', 'x'],    // left_ankle
  ['right_thigh', 'y'],  // right_hip_yaw
  ['right_thigh', 'z'],  // right_hip_roll
  ['right_thigh', 'x'],  // right_hip_pitch
  ['right_shin', 'x'],   // right_knee
  ['right_foot', 'x'],   // right_ankle
  ['torso', 'y'],        // torso
  ['left_upper_arm', 'x'],   // left_shoulder_pitch
  ['left_upper_arm', 'z'],   // left_shoulder_roll
  ['left_forearm', 'x'],     // left_elbow
  ['right_upper_arm', 'x'],  // right_shoulder_pitch
  ['right_upper_arm', 'z'],  // right_shoulder_roll
  ['right_forearm', 'x'],    // right_elbow
  ['left_hand', 'y'],    // left_wrist_roll
  ['right_hand', 'y'],   // right_wrist_roll
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
  '/assets/h1.glb',
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

  // Update robot position & heading
  const [px, py, pz] = frame.position;
  robotGroup.position.set(px, py, pz);
  robotGroup.rotation.y = frame.heading;

  // Drive the active robot rig (procedural or GLB) from the joint stream.
  if (frame.joints) applyJoints(frame.joints);

  // Follow camera
  const behind = new THREE.Vector3(
    px - Math.sin(frame.heading) * 6,
    py + 3,
    pz - Math.cos(frame.heading) * 6,
  );
  camera.position.lerp(behind, 0.04);
  controls.target.lerp(new THREE.Vector3(px, py + 1, pz), 0.08);

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
