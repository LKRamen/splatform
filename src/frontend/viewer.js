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
// Robot — load GLB or build capsule placeholder
// ------------------------------------------------------------------
let robotGroup = new THREE.Group();
scene.add(robotGroup);

// Joint bone map (populated when GLB loads)
const jointBones = {};

const JOINT_NAMES = [
  'left_hip_yaw','left_hip_roll','left_hip_pitch','left_knee','left_ankle',
  'right_hip_yaw','right_hip_roll','right_hip_pitch','right_knee','right_ankle',
  'torso',
  'left_shoulder_pitch','left_shoulder_roll','left_shoulder_yaw','left_elbow',
  'right_shoulder_pitch','right_shoulder_roll','right_shoulder_yaw','right_elbow',
];

function buildCapsulePlaceholder() {
  const mat = new THREE.MeshLambertMaterial({ color: 0x00e5cc });
  // Torso
  const torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.18, 0.6, 4, 8), mat);
  torso.position.set(0, 1.0, 0);
  // Head
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.12, 8, 8), mat);
  head.position.set(0, 1.55, 0);
  // Arms
  for (const sx of [-1, 1]) {
    const arm = new THREE.Mesh(new THREE.CapsuleGeometry(0.05, 0.4, 4, 8), mat);
    arm.position.set(sx * 0.3, 0.9, 0);
    robotGroup.add(arm);
  }
  // Legs
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
    robotGroup.add(gltf.scene);
    // Map bone names to joints
    gltf.scene.traverse((obj) => {
      if (obj.isBone || obj.isSkinnedMesh) {
        const name = obj.name.toLowerCase().replace(/_link$/, '');
        if (JOINT_NAMES.includes(name)) jointBones[name] = obj;
      }
    });
  },
  undefined,
  () => buildCapsulePlaceholder()
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

  // Update joint bones if GLB is loaded
  frame.joints.forEach((angle, i) => {
    const name = JOINT_NAMES[i];
    const bone = jointBones[name];
    if (bone) bone.rotation.x = angle;  // simplified: all revolute on X
  });

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
