// Receives wsframe events from viewer.js and renders animated score bars.

const DIMS = [
  { key: 'waypoint',   label: 'Waypoint Efficiency', weight: 0.30, color: '#00e5cc' },
  { key: 'gait',       label: 'Gait Stability',       weight: 0.25, color: '#4488ff' },
  { key: 'clearance',  label: 'Obstacle Clearance',   weight: 0.20, color: '#88aaff' },
  { key: 'energy',     label: 'Energy',                weight: 0.15, color: '#ffaa44' },
  { key: 'completion', label: 'Completion',            weight: 0.10, color: '#aa44ff' },
];

const panel = document.getElementById('score-panel');

// Build DOM
const totalEl = document.createElement('div');
totalEl.style.cssText = 'display:flex;align-items:baseline;gap:8px;margin-bottom:12px;';
totalEl.innerHTML = `<span style="font-size:32px;font-weight:700;color:#00e5cc" id="total-score">--</span>
  <span style="font-size:16px;font-weight:600;color:#888" id="total-grade">?</span>
  <span style="font-size:11px;color:#555;margin-left:auto">total</span>`;
panel.appendChild(totalEl);

const bars = {};
DIMS.forEach(({ key, label, color }) => {
  const row = document.createElement('div');
  row.style.cssText = 'margin-bottom:8px;';
  row.innerHTML = `
    <div style="display:flex;justify-content:space-between;font-size:10px;color:#888;margin-bottom:3px;">
      <span>${label}</span><span id="score-val-${key}">--</span>
    </div>
    <div style="background:#1a1a28;border-radius:3px;height:5px;overflow:hidden;">
      <div id="score-bar-${key}" style="height:100%;width:0%;background:${color};border-radius:3px;transition:width 0.15s ease;"></div>
    </div>`;
  panel.appendChild(row);
  bars[key] = {
    bar: row.querySelector(`#score-bar-${key}`),
    val: row.querySelector(`#score-val-${key}`),
  };
});

// Sparkline canvas
const sparkCanvas = document.createElement('canvas');
sparkCanvas.width = 268; sparkCanvas.height = 40;
sparkCanvas.style.cssText = 'display:block;margin-top:10px;width:100%;';
panel.appendChild(sparkCanvas);
const sparkCtx = sparkCanvas.getContext('2d');
const sparkData = [];
const SPARK_LEN = 30;

function gradeFromScore(s) {
  if (s >= 0.90) return 'S';
  if (s >= 0.75) return 'A';
  if (s >= 0.60) return 'B';
  if (s >= 0.45) return 'C';
  if (s >= 0.30) return 'D';
  return 'F';
}

function drawSparkline() {
  const w = sparkCanvas.width, h = sparkCanvas.height;
  sparkCtx.clearRect(0, 0, w, h);
  if (sparkData.length < 2) return;
  const mn = Math.min(...sparkData), mx = Math.max(...sparkData, mn + 0.01);
  sparkCtx.strokeStyle = '#00e5cc';
  sparkCtx.lineWidth = 1.5;
  sparkCtx.beginPath();
  sparkData.forEach((v, i) => {
    const x = (i / (SPARK_LEN - 1)) * w;
    const y = h - ((v - mn) / (mx - mn)) * (h - 4) - 2;
    i === 0 ? sparkCtx.moveTo(x, y) : sparkCtx.lineTo(x, y);
  });
  sparkCtx.stroke();
}

window.addEventListener('wsframe', (e) => {
  const { scores } = e.detail;
  if (!scores) return;

  DIMS.forEach(({ key }) => {
    const raw = scores[key] ?? 0;
    // Normalise to [0,1] for display (clamp)
    const norm = Math.max(0, Math.min(1, (raw + 1) / 2));
    bars[key].bar.style.width = `${(norm * 100).toFixed(1)}%`;
    bars[key].val.textContent = raw.toFixed(3);
  });

  const total = scores.total ?? 0;
  const normTotal = Math.max(0, Math.min(1, (total + 1) / 2));
  document.getElementById('total-score').textContent = (normTotal * 100).toFixed(0);
  document.getElementById('total-grade').textContent = gradeFromScore(normTotal);

  sparkData.push(normTotal);
  if (sparkData.length > SPARK_LEN) sparkData.shift();
  drawSparkline();
});

// ------------------------------------------------------------------
// Training Progress chart (Chart.js)
// ------------------------------------------------------------------
const chartCanvas = document.getElementById('reward-chart');
if (chartCanvas) {
  import('https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js')
    .then(() => {
      const { Chart } = window;
      if (!Chart) return;
      new Chart(chartCanvas, {
        type: 'line',
        data: {
          labels: ['v1 (10k)', 'v2 (30k)', 'v3 (60k)'],
          datasets: [{
            label: 'Mean Episode Reward',
            data: [34, 58, 79],
            borderColor: '#00e5cc',
            backgroundColor: 'rgba(0,229,204,0.08)',
            pointBackgroundColor: '#00e5cc',
            tension: 0.4,
            fill: true,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: ctx => ` ${ctx.parsed.y}` } },
          },
          scales: {
            x: { ticks: { color: '#666680', font: { size: 10 } }, grid: { color: '#1e1e2e' } },
            y: { ticks: { color: '#666680', font: { size: 10 } }, grid: { color: '#1e1e2e' } },
          },
        },
      });
    })
    .catch(() => {});
}
