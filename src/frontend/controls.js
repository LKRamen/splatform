import { connectWS, setWaypointMarkers, getFloorHitPoint } from '/ui/viewer.js';

const checkpointSelect = document.getElementById('checkpoint-select');
const btnEpisode       = document.getElementById('btn-episode');
const btnAuto          = document.getElementById('btn-auto');
const btnWatch         = document.getElementById('btn-watch');
const btnClearWp       = document.getElementById('btn-clear-wp');
const wpList           = document.getElementById('waypoint-list');
const viewport         = document.getElementById('viewport');

let waypoints = [[5.0, 0.0]];   // default: [x, z]
let mode = 'auto';

// ------------------------------------------------------------------
// Checkpoint selector — reconnect on change
// ------------------------------------------------------------------
checkpointSelect.addEventListener('change', () => {
  connectWS(checkpointSelect.value);
});

// ------------------------------------------------------------------
// New Episode
// ------------------------------------------------------------------
btnEpisode.addEventListener('click', async () => {
  const body = { waypoints: waypoints.map(([x, z]) => [x, z]) };
  await fetch('http://localhost:8765/waypoints', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).catch(() => {});
  connectWS(checkpointSelect.value);
});

// ------------------------------------------------------------------
// Mode toggle
// ------------------------------------------------------------------
btnAuto.addEventListener('click', () => {
  mode = 'auto';
  btnAuto.classList.add('active');
  btnWatch.classList.remove('active');
});
btnWatch.addEventListener('click', () => {
  mode = 'watch';
  btnWatch.classList.add('active');
  btnAuto.classList.remove('active');
});

// ------------------------------------------------------------------
// Waypoint list rendering
// ------------------------------------------------------------------
function renderWpList() {
  wpList.innerHTML = '';
  waypoints.forEach(([x, z], i) => {
    const li = document.createElement('li');
    li.innerHTML = `<span>#${i + 1} (${x.toFixed(1)}, ${z.toFixed(1)})</span><span class="del" data-i="${i}">✕</span>`;
    wpList.appendChild(li);
  });
  setWaypointMarkers(waypoints);
}

wpList.addEventListener('click', (e) => {
  const delBtn = e.target.closest('[data-i]');
  if (!delBtn) return;
  waypoints.splice(Number(delBtn.dataset.i), 1);
  renderWpList();
});

btnClearWp.addEventListener('click', () => {
  waypoints = [];
  renderWpList();
});

// ------------------------------------------------------------------
// Click-to-place waypoints on floor via raycasting
// ------------------------------------------------------------------
let _clickStart = null;

viewport.addEventListener('mousedown', (e) => {
  _clickStart = { x: e.clientX, y: e.clientY };
});

viewport.addEventListener('mouseup', (e) => {
  if (!_clickStart) return;
  const dx = Math.abs(e.clientX - _clickStart.x);
  const dy = Math.abs(e.clientY - _clickStart.y);
  _clickStart = null;
  if (dx > 5 || dy > 5) return;   // was a drag, not a click

  const hit = getFloorHitPoint(e.clientX, e.clientY);
  if (!hit || isNaN(hit.x) || isNaN(hit.z)) return;
  waypoints.push([parseFloat(hit.x.toFixed(2)), parseFloat(hit.z.toFixed(2))]);
  renderWpList();
});

// Initial render
renderWpList();
