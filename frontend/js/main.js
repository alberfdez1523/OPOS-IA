/**
 * TimeSeries AI — Landing Page JavaScript
 * Animated chart, stats loading, interactions
 */

const API_BASE = 'http://localhost:8000/api';

// ============================================
// Animated Time Series Chart (Canvas)
// ============================================
function initChart() {
  const canvas = document.getElementById('timeseries-chart');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;

  function resize() {
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = 200 * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = '200px';
    ctx.scale(dpr, dpr);
  }

  resize();
  window.addEventListener('resize', resize);

  // Generate fake time series data
  let data = [];
  const numPoints = 60;
  let value = 2000;

  for (let i = 0; i < numPoints; i++) {
    // Random walk with trend and seasonality
    const trend = 0.5;
    const seasonal = Math.sin(i * 0.3) * 15;
    const noise = (Math.random() - 0.5) * 20;
    value += trend + noise;
    data.push(value + seasonal);
  }

  function drawChart() {
    const w = canvas.width / dpr;
    const h = canvas.height / dpr;

    ctx.clearRect(0, 0, w, h);

    const min = Math.min(...data) - 10;
    const max = Math.max(...data) + 10;
    const range = max - min;

    const stepX = w / (data.length - 1);

    // Gradient fill
    const gradient = ctx.createLinearGradient(0, 0, 0, h);
    gradient.addColorStop(0, 'rgba(108, 92, 231, 0.3)');
    gradient.addColorStop(1, 'rgba(108, 92, 231, 0)');

    // Draw fill
    ctx.beginPath();
    ctx.moveTo(0, h);
    for (let i = 0; i < data.length; i++) {
      const x = i * stepX;
      const y = h - ((data[i] - min) / range) * (h - 20);
      if (i === 0) ctx.lineTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.lineTo(w, h);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Draw line
    ctx.beginPath();
    for (let i = 0; i < data.length; i++) {
      const x = i * stepX;
      const y = h - ((data[i] - min) / range) * (h - 20);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = '#6c5ce7';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw last point glow
    const lastX = (data.length - 1) * stepX;
    const lastY = h - ((data[data.length - 1] - min) / range) * (h - 20);

    ctx.beginPath();
    ctx.arc(lastX, lastY, 6, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(108, 92, 231, 0.3)';
    ctx.fill();

    ctx.beginPath();
    ctx.arc(lastX, lastY, 3, 0, Math.PI * 2);
    ctx.fillStyle = '#6c5ce7';
    ctx.fill();

    // Update value display
    const valueEl = document.getElementById('chart-value');
    if (valueEl) {
      const notes = ['Do', 'Re', 'Mi', 'Fa', 'Sol', 'La', 'Si'];
      const note = notes[Math.floor(Math.abs(data[data.length - 1])) % 7];
      valueEl.textContent = `🎵 ${note} · ${(220 + (data[data.length - 1] % 440)).toFixed(0)} Hz`;
    }
  }

  // Animate: add new data point every 2 seconds
  function tick() {
    const last = data[data.length - 1];
    const trend = 0.5;
    const seasonal = Math.sin(data.length * 0.3) * 15;
    const noise = (Math.random() - 0.5) * 20;
    const newVal = last + trend + noise + Math.sin(data.length * 0.1) * 5;
    data.push(newVal);
    if (data.length > 80) data.shift();
    drawChart();
  }

  drawChart();
  setInterval(tick, 2000);
}


// ============================================
// Load Stats from API
// ============================================
async function loadStats() {
  try {
    const res = await fetch(`${API_BASE}/stats`);
    if (res.ok) {
      const data = await res.json();
      const chunksEl = document.getElementById('stat-chunks');
      if (chunksEl) chunksEl.textContent = data.chunks || '—';

      const onlineEl = document.getElementById('stat-online');
      if (onlineEl) onlineEl.textContent = data.status === 'active' ? '●' : '○';
    }
  } catch (e) {
    console.log('API not available, using defaults');
    const chunksEl = document.getElementById('stat-chunks');
    if (chunksEl) chunksEl.textContent = '271';
    const onlineEl = document.getElementById('stat-online');
    if (onlineEl) onlineEl.textContent = '●';
  }
}


// ============================================
// Init
// ============================================
document.addEventListener('DOMContentLoaded', () => {
  initChart();
  loadStats();
});
