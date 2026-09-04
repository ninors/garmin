// Engine PWA Garmin Hub & Telemetry
document.addEventListener('DOMContentLoaded', () => {
  let appData = { activities: [], workouts: [] };
  let deferredPrompt = null;
  let currentCharts = {};
  let gpxMapInstance = null;

  // DOM Elements
  const dockTabs = document.querySelectorAll('.dock-tab');
  const tabPanels = document.querySelectorAll('.tab-panel');
  const activityFeed = document.getElementById('activityFeed');
  const pwaInstallBtn = document.getElementById('pwaInstallBtn');
  
  // Stats
  const summaryAvgHr = document.getElementById('summaryAvgHr');
  const summarySpeed = document.getElementById('summarySpeed');
  const summaryResp = document.getElementById('summaryResp');
  const summaryDistance = document.getElementById('summaryDistance');

  // Modal
  const telemetryModal = document.getElementById('telemetryModal');
  const closeModalBtn = document.getElementById('closeModalBtn');
  const modalActTitle = document.getElementById('modalActTitle');
  const modalHr = document.getElementById('modalHr');
  const modalSpeed = document.getElementById('modalSpeed');
  const modalResp = document.getElementById('modalResp');

  // GPX Upload
  const gpxDropzone = document.getElementById('gpxDropzone');
  const gpxFileInput = document.getElementById('gpxFileInput');
  const gpxPreviewContainer = document.getElementById('gpxPreviewContainer');
  const gpxName = document.getElementById('gpxName');
  const gpxStats = document.getElementById('gpxStats');
  const sendToWatchBtn = document.getElementById('sendToWatchBtn');

  // 1. Service Worker PWA Registration
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('./sw.js').then(() => {
      console.log('PWA Service Worker actif');
    }).catch(err => console.warn('SW error:', err));
  }

  // 2. PWA Install Banner
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    pwaInstallBtn.classList.remove('hidden');
  });

  pwaInstallBtn.addEventListener('click', () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      deferredPrompt.userChoice.then(() => {
        pwaInstallBtn.classList.add('hidden');
        deferredPrompt = null;
      });
    }
  });

  // 3. Tab Switching
  dockTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      dockTabs.forEach(t => t.classList.remove('active'));
      tabPanels.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetId = tab.dataset.tab;
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) targetPanel.classList.add('active');
    });
  });

  // 4. Data Loading
  async function loadData() {
    try {
      const res = await fetch('data/data.json');
      if (!res.ok) throw new Error('data.json non trouve');
      appData = await res.json();
    } catch (e) {
      console.warn('Chargement des données démo :', e.message);
      appData = getDemoData();
    } finally {
      renderSummary();
      renderActivities();
    }
  }

  function getDemoData() {
    return {
      activities: [
        {
          id: "act_101",
          name: "Triathlon Entraînement - Vélo & Course",
          type: "cycling",
          distance_km: 42.5,
          duration_min: 85.0,
          avg_speed_kmh: 30.0,
          avg_hr: 154,
          max_hr: 178,
          avg_respiration: 28.5,
          date: new Date().toISOString(),
          telemetry: {
            heart_rate: [120, 135, 148, 155, 160, 162, 158, 154, 165, 172, 168, 155],
            speed: [22, 28, 31, 32, 30, 29, 33, 34, 31, 28, 25, 29],
            elevation: [120, 125, 140, 160, 185, 210, 190, 170, 150, 130, 122, 120],
            respiration: [20, 22, 26, 28, 30, 31, 29, 28, 30, 32, 29, 27]
          }
        },
        {
          id: "act_102",
          name: "Session VMA Course à pied",
          type: "running",
          distance_km: 10.2,
          duration_min: 44.0,
          avg_speed_kmh: 13.9,
          avg_pace_minkm: 4.31,
          avg_hr: 162,
          max_hr: 184,
          avg_respiration: 32.0,
          date: new Date(Date.now() - 86400000).toISOString(),
          telemetry: {
            heart_rate: [115, 140, 158, 165, 175, 182, 178, 165, 172, 184, 170, 140],
            speed: [10, 12, 14, 15, 16, 16.5, 14, 13, 15, 16.8, 14, 10],
            elevation: [40, 42, 45, 48, 52, 55, 53, 50, 46, 43, 41, 40],
            respiration: [22, 25, 29, 32, 35, 38, 34, 31, 33, 36, 30, 24]
          }
        }
      ]
    };
  }

  function renderSummary() {
    const acts = appData.activities || [];
    if (acts.length === 0) return;

    let totalDist = 0;
    let maxSpd = 0;
    let hrSum = 0, hrCount = 0;
    let respSum = 0, respCount = 0;

    acts.forEach(a => {
      totalDist += a.distance_km || 0;
      if ((a.avg_speed_kmh || 0) > maxSpd) maxSpd = a.avg_speed_kmh;
      if (a.avg_hr) { hrSum += a.avg_hr; hrCount++; }
      if (a.avg_respiration) { respSum += a.avg_respiration; respCount++; }
    });

    summaryDistance.textContent = `${totalDist.toFixed(1)} km`;
    summarySpeed.textContent = `${maxSpd.toFixed(1)} km/h`;
    summaryAvgHr.textContent = hrCount > 0 ? `${Math.round(hrSum / hrCount)} bpm` : '-- bpm';
    summaryResp.textContent = respCount > 0 ? `${(respSum / respCount).toFixed(1)} br/min` : '-- br/min';
  }

  function renderActivities() {
    activityFeed.innerHTML = '';
    const acts = appData.activities || [];

    if (acts.length === 0) {
      activityFeed.innerHTML = '<p class="subtitle" style="grid-column:1/-1; text-align:center;">Aucune activité enregistrée.</p>';
      return;
    }

    acts.forEach(act => {
      const card = document.createElement('div');
      card.className = 'activity-card';

      let badgeClass = 'badge-run';
      let badgeIcon = 'fa-person-running';
      if (act.type.includes('cycl') || act.type.includes('ride')) {
        badgeClass = 'badge-ride';
        badgeIcon = 'fa-person-biking';
      } else if (act.type.includes('swim')) {
        badgeClass = 'badge-swim';
        badgeIcon = 'fa-person-swimming';
      }

      const dateStr = act.date ? new Date(act.date).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';

      card.innerHTML = `
        <div class="card-top">
          <div>
            <h3 class="act-title">${escapeHtml(act.name)}</h3>
            <span class="act-date"><i class="fa-regular fa-clock"></i> ${dateStr}</span>
          </div>
          <span class="sport-badge ${badgeClass}"><i class="fa-solid ${badgeIcon}"></i> ${act.type}</span>
        </div>

        <div class="telemetry-row">
          <div class="t-item"><span class="t-val">${act.distance_km || 0} km</span><span class="t-lbl">Distance</span></div>
          <div class="t-item"><span class="t-val">${act.duration_min || 0} min</span><span class="t-lbl">Durée</span></div>
          <div class="t-item"><span class="t-val">${act.avg_hr ? act.avg_hr + ' bpm' : '--'}</span><span class="t-lbl">Fréq. Cardiaque</span></div>
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.8rem;">
          <span class="summary-lbl"><i class="fa-solid fa-lungs text-apple-green"></i> Resp: ${act.avg_respiration || '--'} br/min</span>
          <button class="btn-liquid btn-glass btn-sm view-telemetry-btn">
            <i class="fa-solid fa-chart-simple"></i> Graphiques Capteurs
          </button>
        </div>
      `;

      card.querySelector('.view-telemetry-btn').addEventListener('click', () => {
        openTelemetryModal(act);
      });

      activityFeed.appendChild(card);
    });
  }

  // 5. Modal Telemetry & Chart.js Rendering
  function openTelemetryModal(act) {
    modalActTitle.textContent = act.name;
    modalHr.textContent = act.avg_hr ? `${act.avg_hr} bpm (Max: ${act.max_hr || '--'})` : '--';
    modalSpeed.textContent = act.avg_speed_kmh ? `${act.avg_speed_kmh} km/h` : '--';
    modalResp.textContent = act.avg_respiration ? `${act.avg_respiration} br/min` : '--';

    const tel = act.telemetry || {};
    const hrData = tel.heart_rate || [120, 130, 145, 150, 160, 155, 140];
    const speedData = tel.speed || [20, 25, 28, 30, 29, 27, 22];
    const elevData = tel.elevation || [100, 105, 120, 140, 130, 115, 100];
    const labels = hrData.map((_, i) => `${i * 2}m`);

    // Destroy old charts if exist
    if (currentCharts.hrChart) currentCharts.hrChart.destroy();
    if (currentCharts.speedChart) currentCharts.speedChart.destroy();

    // Chart 1: Heart Rate
    const ctx1 = document.getElementById('hrChart').getContext('2d');
    currentCharts.hrChart = new Chart(ctx1, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Fréquence Cardiaque (BPM)',
          data: hrData,
          borderColor: '#ff5e4d',
          backgroundColor: 'rgba(255, 94, 77, 0.15)',
          fill: true,
          tension: 0.35,
          borderWidth: 2.5
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: false } }
      }
    });

    // Chart 2: Speed & Altitude
    const ctx2 = document.getElementById('speedChart').getContext('2d');
    currentCharts.speedChart = new Chart(ctx2, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Vitesse (km/h)',
            data: speedData,
            borderColor: '#007aff',
            backgroundColor: 'rgba(0, 122, 255, 0.1)',
            fill: true,
            tension: 0.35,
            yAxisID: 'y'
          },
          {
            label: 'Altitude (m)',
            data: elevData,
            borderColor: '#34c759',
            borderDash: [5, 5],
            fill: false,
            tension: 0.35,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        scales: {
          y: { type: 'linear', position: 'left' },
          y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false } }
        }
      }
    });

    telemetryModal.classList.remove('hidden');
  }

  closeModalBtn.addEventListener('click', () => telemetryModal.classList.add('hidden'));

  // 6. GPX Drag & Drop Parser & Leaflet Map
  gpxDropzone.addEventListener('click', () => gpxFileInput.click());
  gpxDropzone.addEventListener('dragover', (e) => { e.preventDefault(); gpxDropzone.classList.add('dragover'); });
  gpxDropzone.addEventListener('dragleave', () => gpxDropzone.classList.remove('dragover'));
  gpxDropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    gpxDropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) processGpxFile(e.dataTransfer.files[0]);
  });
  gpxFileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) processGpxFile(e.target.files[0]);
  });

  function processGpxFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      const gpxText = e.target.result;
      const parser = new DOMParser();
      const xml = parser.parseFromString(gpxText, "text/xml");

      const nameEl = xml.querySelector("name");
      const title = nameEl ? nameEl.textContent : file.name;
      const trkpts = xml.querySelectorAll("trkpt");

      const coords = [];
      trkpts.forEach(pt => {
        const lat = parseFloat(pt.getAttribute("lat"));
        const lon = parseFloat(pt.getAttribute("lon"));
        if (!isNaN(lat) && !isNaN(lon)) coords.push([lat, lon]);
      });

      gpxName.textContent = title;
      gpxStats.textContent = `Points: ${coords.length} | Fichier: ${file.name}`;
      gpxPreviewContainer.classList.remove('hidden');

      // Initialize Leaflet Map
      setTimeout(() => {
        if (gpxMapInstance) gpxMapInstance.remove();
        if (coords.length > 0) {
          gpxMapInstance = L.map('gpxMap').setView(coords[0], 13);
          L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap'
          }).addTo(gpxMapInstance);

          const polyline = L.polyline(coords, { color: '#ff5e4d', weight: 4 }).addTo(gpxMapInstance);
          gpxMapInstance.fitBounds(polyline.getBounds());
        }
      }, 100);
    };
    reader.readAsText(file);
  }

  sendToWatchBtn.addEventListener('click', () => {
    alert('🚀 Fichier GPX envoyé à la Forerunner 165 Music ! Démarrez votre activité Triathlon sur la montre.');
  });

  function escapeHtml(str) {
    return str ? str.replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m])) : '';
  }

  loadData();
});
