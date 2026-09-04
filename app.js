// Garmin GPX/FIT Application Engine
document.addEventListener('DOMContentLoaded', () => {
  let appData = {
    last_sync: null,
    courses: [],
    workouts: [],
    activities: []
  };

  let activeTab = 'courses';
  let searchQuery = '';

  // DOM Elements
  const loadingSpinner = document.getElementById('loadingSpinner');
  const emptyState = document.getElementById('emptyState');
  const itemsContainer = document.getElementById('itemsContainer');
  const searchInput = document.getElementById('searchInput');
  const tabBtns = document.querySelectorAll('.tab-btn');
  const downloadZipBtn = document.getElementById('downloadZipBtn');
  const triggerSyncBtn = document.getElementById('triggerSyncBtn');
  const syncModal = document.getElementById('syncModal');
  const closeModalBtn = document.getElementById('closeModalBtn');
  const githubActionsLink = document.getElementById('githubActionsLink');

  // Stats counters
  const statCourses = document.getElementById('statCourses');
  const statWorkouts = document.getElementById('statWorkouts');
  const statActivities = document.getElementById('statActivities');
  const statLastSync = document.getElementById('statLastSync');
  
  const tabCountCourses = document.getElementById('tabCountCourses');
  const tabCountWorkouts = document.getElementById('tabCountWorkouts');
  const tabCountActivities = document.getElementById('tabCountActivities');

  // Set GitHub Link automatically based on current hostname / path
  if (githubActionsLink) {
    const currentUrl = window.location.href;
    if (currentUrl.includes('github.io')) {
      const parts = window.location.pathname.split('/').filter(Boolean);
      const repoName = parts[0] || '';
      const user = window.location.hostname.split('.')[0];
      githubActionsLink.href = `https://github.com/${user}/${repoName}/actions`;
    } else {
      githubActionsLink.href = 'https://github.com';
    }
  }

  // Load Data
  async function loadGarminData() {
    try {
      const response = await fetch('data/data.json');
      if (!response.ok) {
        throw new Error('Fichier data.json non trouvé (Première synchro non effectuée)');
      }
      appData = await response.json();
    } catch (err) {
      console.warn('Utilisation des données de démonstration :', err.message);
      // Données de démonstration visuelle si la première synchro n'a pas encore tourné
      appData = getDemoData();
    } finally {
      loadingSpinner.classList.add('hidden');
      updateStats();
      renderItems();
    }
  }

  function getDemoData() {
    return {
      last_sync: new Date().toISOString(),
      courses: [
        {
          id: 'demo_1',
          name: 'Boucle Trail Mont-Blanc (Exemple)',
          distance_km: 18.5,
          elevation_m: 920,
          date: new Date().toISOString(),
          gpx_path: '#demo',
          fit_path: '#demo'
        },
        {
          id: 'demo_2',
          name: 'Sortie Vélo Route 60km (Exemple)',
          distance_km: 62.4,
          elevation_m: 450,
          date: new Date().toISOString(),
          gpx_path: '#demo',
          fit_path: '#demo'
        }
      ],
      workouts: [
        {
          id: 'demo_3',
          name: 'Séance VMA 10x400m (Exemple)',
          sport: 'running',
          date: new Date().toISOString(),
          file_path: '#demo'
        }
      ],
      activities: [
        {
          id: 'demo_4',
          name: 'Course à pied matinale (Exemple)',
          type: 'running',
          distance_km: 10.2,
          duration_min: 48.5,
          date: new Date().toISOString(),
          gpx_path: '#demo',
          fit_path: '#demo'
        }
      ]
    };
  }

  function updateStats() {
    const cCount = appData.courses ? appData.courses.length : 0;
    const wCount = appData.workouts ? appData.workouts.length : 0;
    const aCount = appData.activities ? appData.activities.length : 0;

    statCourses.textContent = cCount;
    statWorkouts.textContent = wCount;
    statActivities.textContent = aCount;

    tabCountCourses.textContent = cCount;
    tabCountWorkouts.textContent = wCount;
    tabCountActivities.textContent = aCount;

    if (appData.last_sync) {
      const syncDate = new Date(appData.last_sync);
      statLastSync.textContent = syncDate.toLocaleDateString('fr-FR', {
        day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
      });
    } else {
      statLastSync.textContent = 'En attente...';
    }
  }

  function renderItems() {
    itemsContainer.innerHTML = '';
    let items = appData[activeTab] || [];

    // Filter by search
    if (searchQuery.trim() !== '') {
      const q = searchQuery.toLowerCase();
      items = items.filter(item => 
        (item.name && item.name.toLowerCase().includes(q)) ||
        (item.date && item.date.toLowerCase().includes(q))
      );
    }

    if (items.length === 0) {
      emptyState.classList.remove('hidden');
      return;
    }

    emptyState.classList.add('hidden');

    items.forEach(item => {
      const card = createCardElement(item, activeTab);
      itemsContainer.appendChild(card);
    });
  }

  function createCardElement(item, category) {
    const card = document.createElement('div');
    card.className = 'card';

    let badgeClass = 'badge-course';
    let badgeText = 'Parcours';
    let metaHTML = '';
    let buttonsHTML = '';

    const formattedDate = item.date ? new Date(item.date).toLocaleDateString('fr-FR') : 'Date inconnue';

    if (category === 'courses') {
      badgeClass = 'badge-course';
      badgeText = 'Parcours';
      metaHTML = `
        <div class="meta-item"><i class="fa-solid fa-ruler-horizontal"></i> ${item.distance_km || 0} km</div>
        <div class="meta-item"><i class="fa-solid fa-mountain"></i> ${item.elevation_m || 0} m D+</div>
        <div class="meta-item"><i class="fa-regular fa-calendar"></i> ${formattedDate}</div>
      `;
      buttonsHTML = `
        ${item.gpx_path ? `<a href="${item.gpx_path}" download class="btn btn-sm btn-gpx"><i class="fa-solid fa-download"></i> GPX</a>` : ''}
        ${item.fit_path ? `<a href="${item.fit_path}" download class="btn btn-sm btn-fit"><i class="fa-solid fa-download"></i> FIT</a>` : ''}
      `;
    } else if (category === 'workouts') {
      badgeClass = 'badge-workout';
      badgeText = 'Entraînement';
      metaHTML = `
        <div class="meta-item"><i class="fa-solid fa-bolt"></i> ${item.sport || 'Général'}</div>
        <div class="meta-item"><i class="fa-regular fa-calendar"></i> ${formattedDate}</div>
      `;
      buttonsHTML = `
        ${item.file_path ? `<a href="${item.file_path}" download class="btn btn-sm btn-fit"><i class="fa-solid fa-download"></i> Entraînement</a>` : ''}
      `;
    } else if (category === 'activities') {
      badgeClass = 'badge-activity';
      badgeText = 'Activité';
      metaHTML = `
        <div class="meta-item"><i class="fa-solid fa-stopwatch"></i> ${item.duration_min || 0} min</div>
        <div class="meta-item"><i class="fa-solid fa-ruler-horizontal"></i> ${item.distance_km || 0} km</div>
        <div class="meta-item"><i class="fa-regular fa-calendar"></i> ${formattedDate}</div>
      `;
      buttonsHTML = `
        ${item.gpx_path ? `<a href="${item.gpx_path}" download class="btn btn-sm btn-gpx"><i class="fa-solid fa-download"></i> GPX</a>` : ''}
        ${item.fit_path ? `<a href="${item.fit_path}" download class="btn btn-sm btn-fit"><i class="fa-solid fa-download"></i> FIT</a>` : ''}
      `;
    }

    card.innerHTML = `
      <span class="card-badge ${badgeClass}">${badgeText}</span>
      <h3 class="card-title">${escapeHtml(item.name)}</h3>
      <div class="card-meta">${metaHTML}</div>
      <div class="card-actions">${buttonsHTML}</div>
    `;

    return card;
  }

  function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/[&<>"']/g, function(m) {
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'}[m];
    });
  }

  // ZIP Generation (Everything in 1 click)
  async function downloadAllZip() {
    if (typeof JSZip === 'undefined') {
      alert('La bibliothèque JSZip est en cours de chargement, réessayez dans une seconde.');
      return;
    }

    const zip = new JSZip();
    const coursesFolder = zip.folder("parcours");
    const workoutsFolder = zip.folder("planifications");
    const activitiesFolder = zip.folder("activites");

    let count = 0;
    downloadZipBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Compression...';
    downloadZipBtn.disabled = true;

    try {
      // Helper to fetch file and add to zip
      async function addFileToZip(folder, path, filename) {
        if (!path || path === '#demo') return;
        try {
          const res = await fetch(path);
          if (res.ok) {
            const blob = await res.blob();
            folder.file(filename, blob);
            count++;
          }
        } catch (e) {
          console.warn('Impossible d\'ajouter au ZIP:', path);
        }
      }

      // Add Courses
      for (const course of (appData.courses || [])) {
        if (course.gpx_path) {
          const name = course.gpx_path.split('/').pop();
          await addFileToZip(coursesFolder, course.gpx_path, name);
        }
        if (course.fit_path) {
          const name = course.fit_path.split('/').pop();
          await addFileToZip(coursesFolder, course.fit_path, name);
        }
      }

      // Add Workouts
      for (const w of (appData.workouts || [])) {
        if (w.file_path) {
          const name = w.file_path.split('/').pop();
          await addFileToZip(workoutsFolder, w.file_path, name);
        }
      }

      // Add Activities
      for (const a of (appData.activities || [])) {
        if (a.gpx_path) {
          const name = a.gpx_path.split('/').pop();
          await addFileToZip(activitiesFolder, a.gpx_path, name);
        }
        if (a.fit_path) {
          const name = a.fit_path.split('/').pop();
          await addFileToZip(activitiesFolder, a.fit_path, name);
        }
      }

      if (count === 0) {
        alert('Aucun fichier GPX/FIT disponible pour le moment. Lancez la synchronisation Garmin !');
      } else {
        const content = await zip.generateAsync({ type: "blob" });
        saveAs(content, `Garmin_Export_${new Date().toISOString().slice(0, 10)}.zip`);
      }
    } catch (err) {
      alert('Erreur lors de la création du fichier ZIP : ' + err.message);
    } finally {
      downloadZipBtn.innerHTML = '<i class="fa-solid fa-file-zipper"></i> <span>Tout Télécharger (.ZIP)</span>';
      downloadZipBtn.disabled = false;
    }
  }

  // Event Listeners
  searchInput.addEventListener('input', (e) => {
    searchQuery = e.target.value;
    renderItems();
  });

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeTab = btn.dataset.tab;
      renderItems();
    });
  });

  downloadZipBtn.addEventListener('click', downloadAllZip);

  triggerSyncBtn.addEventListener('click', () => {
    syncModal.classList.remove('hidden');
  });

  closeModalBtn.addEventListener('click', () => {
    syncModal.classList.add('hidden');
  });

  syncModal.addEventListener('click', (e) => {
    if (e.target === syncModal) {
      syncModal.classList.add('hidden');
    }
  });

  // Init
  loadGarminData();
});
