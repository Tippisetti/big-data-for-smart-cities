// Elements
const riskEl   = document.getElementById('risk');
const adviceEl = document.getElementById('advice');
const typeEl   = document.getElementById('disaster-type');
const statusEl = document.getElementById('status');
const form     = document.getElementById('sensor-form');

let currentLat = null, currentLon = null;
let map = null, marker = null;

// Chart state
let riskHistory = [];
let riskChart = null;

// --- Location detection (GPS → IP fallback) ---
async function detectLocation() {
  if (!navigator.geolocation) return fallbackLocation();
  navigator.geolocation.getCurrentPosition(
    async ({ coords }) => {
      currentLat = coords.latitude;
      currentLon = coords.longitude;
      statusEl.textContent = `Location (GPS): ${currentLat.toFixed(4)}, ${currentLon.toFixed(4)}`;
      initMap(currentLat, currentLon);
      await predict(currentLat, currentLon);
    },
    async () => fallbackLocation(),
    { timeout: 8000 }
  );
}

async function fallbackLocation() {
  try {
    const res = await fetch("https://ipapi.co/json/");
    const d = await res.json();
    currentLat = d.latitude; currentLon = d.longitude;
    statusEl.textContent = `Approx. location: ${d.city}, ${d.country_name}`;
    initMap(currentLat, currentLon);
    await predict(currentLat, currentLon);
  } catch {
    statusEl.textContent = "Unable to detect location.";
  }
}

// --- Map ---
function initMap(lat, lon) {
  if (map) return map.setView([lat, lon], 11);
  map = L.map('map').setView([lat, lon], 11);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19, attribution: '&copy; CARTO | © OSM'
  }).addTo(map);
  marker = L.marker([lat, lon]).addTo(map).bindPopup('Your Location').openPopup();
}

function updateMarker(lat, lon, color, disaster, severity) {
  if (!map) return;
  if (marker) map.removeLayer(marker);
  const pulsing = (severity === 'HIGH' || severity === 'EXTREME');
  const html = `<div class="${pulsing ? 'pulse' : ''}" style="background:${color};"></div>`;
  const icon = L.divIcon({ className: 'custom-risk-icon', html, iconSize: [22,22], iconAnchor: [11,11] });
  marker = L.marker([lat, lon], { icon }).addTo(map);
  marker.bindPopup(`<b>${(disaster || 'NORMAL').toUpperCase()}</b><br>${severity}`).openPopup();
  map.setView([lat, lon], 11);
}

// --- Prediction call ---
async function predict(lat, lon, extras = {}) {
  const month = new Date().getUTCMonth() + 1;
  const payload = { lat, lon, month, ...extras };
  try {
    const res = await fetch('/api/predict', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    if (!json.ok) throw new Error(json.error || "Prediction failed");

    // Risk badge + type + advice
    riskEl.textContent = `Risk: ${(json.probability * 100).toFixed(1)}% • ${json.severity}`;
    riskEl.style.background = json.color;
    riskEl.classList.remove('high','extreme');
    if (json.severity === "HIGH") riskEl.classList.add('high');
    if (json.severity === "EXTREME") riskEl.classList.add('extreme');
    adviceEl.textContent = json.advice;
    typeEl.textContent = (json.predicted_disaster || '—').toUpperCase();

    // Map marker
    updateMarker(lat, lon, json.color, json.predicted_disaster, json.severity);

    // Chart + weather
    updateChart(json.probability, json.color);
    await fetchWeather(lat, lon);
  } catch (e) {
    console.error(e);
    riskEl.textContent = 'Risk unavailable';
    adviceEl.textContent = 'Model not responding.';
  }
}

// Manual sensor override
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const extras = Object.fromEntries(new FormData(form).entries());
  await predict(currentLat, currentLon, extras);
});

// --- Chart (Chart.js) ---
function initChart() {
  const ctx = document.getElementById('riskChart').getContext('2d');
  riskChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'Risk Probability (%)',
        data: [],
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59,130,246,0.2)',
        fill: true, tension: 0.35, pointRadius: 3
      }]
    },
    options: {
      maintainAspectRatio: false,
      scales: {
        x: { ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' } },
        y: { ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' }, min: 0, max: 100 }
      },
      plugins: { legend: { labels: { color: '#e2e8f0' } } }
    }
  });
}

function updateChart(prob, color) {
  const t = new Date().toLocaleTimeString();
  riskHistory.push({ t, p: +(prob * 100).toFixed(1), c: color });
  if (riskHistory.length > 5) riskHistory.shift();

  riskChart.data.labels = riskHistory.map(r => r.t);
  riskChart.data.datasets[0].data = riskHistory.map(r => r.p);
  riskChart.data.datasets[0].borderColor = color;
  riskChart.data.datasets[0].backgroundColor = color + "33"; // light fill
  riskChart.update();
}

// --- Weather panel (Open-Meteo, no key) ---
async function fetchWeather(lat, lon) {
  try {
    const res = await fetch(`/api/weather?lat=${lat}&lon=${lon}`);
    const json = await res.json();
    const w = json.data;
    const box = document.getElementById('weather-summary');
    if (!json.ok || !w) throw new Error("Weather unavailable");
    box.innerHTML = `
      <ul>
        <li><b>🌡️ Temp:</b> ${w.temperature_2m ?? '—'} °C</li>
        <li><b>💨 Wind:</b> ${w.wind_speed_10m ?? '—'} km/h</li>
        <li><b>☁️ Clouds:</b> ${w.cloud_cover ?? '—'} %</li>
        <li><b>🌧️ Rain:</b> ${w.precipitation ?? '—'} mm</li>
      </ul>`;
  } catch {
    document.getElementById('weather-summary').innerHTML = "<p>Unable to load weather data.</p>";
  }
}

// Auto refresh (30s)
setInterval(() => { if (currentLat && currentLon) predict(currentLat, currentLon); }, 30000);

// Boot
window.addEventListener('load', () => {
  detectLocation();
  initChart();
});
