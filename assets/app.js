// assets/app.js
// Version robuste: sanitize + images + affichage corrigé

const THEME_DATA = [
  {
    id: "ordre_public",
    label: "Ordre Public & Mouvements Sociaux",
    subthemes: [
      "Evenement voie publique",
      "Manifestation",
      "Greve",
      "Blocage occupation",
      "Projet Amenagement Conteste",
      "Installation illicite",
      "Squat",
      "Free Rave Teknival"
    ]
  },
  {
    id: "securite",
    label: "Sécurité & Criminalité",
    subthemes: [
      "Delinquance criminalite",
      "Criminalite organisee",
      "Armes",
      "Cybercriminalite",
      "Drones"
    ]
  },
  {
    id: "ideologies",
    label: "Idéologies & Radicalités",
    subthemes: [
      "Radicalisation",
      "Separatisme",
      "Derives sectaires",
      "Proselytisme",
      "Apologie",
      "Terrorisme",
      "Ultra-droite",
      "Ultra-gauche",
      "Animaliste",
      "Ecologie",
      "Survivalisme"
    ]
  },
  {
    id: "politique_institutions",
    label: "Institutions & Politique",
    subthemes: [
      "Visite Officielle",
      "Elections 2027",
      "JOPH 2030",
      "Enseignement Education nationale",
      "Sante",
      "Culte"
    ]
  },
  {
    id: "secteurs_strategiques",
    label: "Secteurs Stratégiques & Environnement",
    subthemes: [
      "Agriculture",
      "Chasse",
      "Transports",
      "Ferroviaire",
      "Nucleaire"
    ]
  }
];

const GEOGRAPHY = {
  zone: "Zone de Défense et de Sécurité Sud",
  regions: [
    {
      name: "OCCITANIE",
      code: "OCC",
      departments: [
        { code: "09", name: "Ariège", cities: ["Foix", "Pamiers"] },
        { code: "11", name: "Aude", cities: ["Carcassonne", "Narbonne"] },
        { code: "12", name: "Aveyron", cities: ["Rodez", "Millau"] },
        { code: "30", name: "Gard", cities: ["Nîmes", "Alès"] },
        { code: "31", name: "Haute-Garonne", cities: ["Toulouse", "Blagnac", "Muret"] },
        { code: "32", name: "Gers", cities: ["Auch"] },
        { code: "34", name: "Hérault", cities: ["Montpellier", "Béziers", "Sète"] },
        { code: "46", name: "Lot", cities: ["Cahors", "Figeac"] },
        { code: "48", name: "Lozère", cities: ["Mende"] },
        { code: "65", name: "Hautes-Pyrénées", cities: ["Tarbes", "Lourdes"] },
        { code: "66", name: "Pyrénées-Orientales", cities: ["Perpignan"] },
        { code: "81", name: "Tarn", cities: ["Albi", "Castres"] },
        { code: "82", name: "Tarn-et-Garonne", cities: ["Montauban"] }
      ]
    },
    {
      name: "PACA",
      code: "PACA",
      departments: [
        { code: "04", name: "Alpes-de-Haute-Provence", cities: ["Digne-les-Bains", "Manosque"] },
        { code: "05", name: "Hautes-Alpes", cities: ["Gap", "Briançon"] },
        { code: "06", name: "Alpes-Maritimes", cities: ["Nice", "Cannes", "Antibes"] },
        { code: "13", name: "Bouches-du-Rhône", cities: ["Marseille", "Aix-en-Provence", "Arles"] },
        { code: "83", name: "Var", cities: ["Toulon", "La Seyne-sur-Mer", "Hyères"] },
        { code: "84", name: "Vaucluse", cities: ["Avignon", "Orange"] }
      ]
    },
    {
      name: "CORSE",
      code: "COR",
      departments: [
        { code: "2A", name: "Corse-du-Sud", cities: ["Ajaccio", "Porto-Vecchio"] },
        { code: "2B", name: "Haute-Corse", cities: ["Bastia", "Corte"] }
      ]
    }
  ]
};

const fallbackItems = [
  {
    title: "Manifestation de rue et tensions sur la voie publique",
    theme: "Ordre Public & Mouvements Sociaux",
    subtheme: "Manifestation",
    region: "OCCITANIE",
    department: "Haute-Garonne",
    city: "Toulouse",
    source: "Média local",
    date: new Date().toISOString(),
    summary: "Signalement de mobilisation de rue avec potentiel impact sur l’ordre public et la circulation.",
    url: "#",
    image: null
  }
];

const state = {
  search: "",
  selectedTheme: "Tous",
  selectedRegion: "Tous",
  selectedDepartment: "Tous",
  selectedCity: "Tous",
  items: []
};

function escapeHtml(unsafe) {
  return String(unsafe)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

document.addEventListener("DOMContentLoaded", () => {
  buildThemeFilters();
  buildRegionFilters();
  buildDepartmentFilters();
  buildCityFilters();
  bindEvents();
  loadData();
});

function bindEvents() {
  document.getElementById("searchInput").addEventListener("input", (e) => {
    state.search = e.target.value.trim().toLowerCase();
    renderCards();
  });

  document.getElementById("refreshBtn").addEventListener("click", () => {
    loadData(true);
  });

  document.getElementById("resetFilters").addEventListener("click", () => {
    state.selectedTheme = "Tous";
    state.selectedRegion = "Tous";
    state.selectedDepartment = "Tous";
    state.selectedCity = "Tous";
    state.search = "";
    document.getElementById("searchInput").value = "";
    renderFilters();
    renderCards();
  });
}

function buildThemeFilters() {
  const container = document.getElementById("themeFilters");
  const items = ["Tous", ...THEME_DATA.map(t => t.label)];
  container.innerHTML = items.map(label => `
    <button class="chip ${state.selectedTheme === label ? "active" : ""}" data-kind="theme" data-value="${escapeHtml(label)}">
      ${escapeHtml(label)}
    </button>
  `).join("");

  container.querySelectorAll(".chip").forEach(btn => {
    btn.addEventListener("click", () => {
      state.selectedTheme = btn.dataset.value;
      renderFilters();
      renderCards();
    });
  });
}

function buildRegionFilters() {
  const container = document.getElementById("regionFilters");
  const items = ["Tous", ...GEOGRAPHY.regions.map(r => r.name)];
  container.innerHTML = items.map(label => `
    <button class="chip ${state.selectedRegion === label ? "active" : ""}" data-kind="region" data-value="${escapeHtml(label)}">
      ${escapeHtml(label)}
    </button>
  `).join("");

  container.querySelectorAll(".chip").forEach(btn => {
    btn.addEventListener("click", () => {
      state.selectedRegion = btn.dataset.value;
      state.selectedDepartment = "Tous";
      state.selectedCity = "Tous";
      renderFilters();
      renderCards();
    });
  });
}

function buildDepartmentFilters() {
  const container = document.getElementById("departmentFilters");
  const region = GEOGRAPHY.regions.find(r => r.name === state.selectedRegion);
  const items = ["Tous"];
  if (region) {
    items.push(...region.departments.map(d => d.name));
  }

  container.innerHTML = items.map(label => `
    <button class="chip ${state.selectedDepartment === label ? "active" : ""}" data-kind="department" data-value="${escapeHtml(label)}">
      ${escapeHtml(label)}
    </button>
  `).join("");

  container.querySelectorAll(".chip").forEach(btn => {
    btn.addEventListener("click", () => {
      state.selectedDepartment = btn.dataset.value;
      state.selectedCity = "Tous";
      renderFilters();
      renderCards();
    });
  });
}

function buildCityFilters() {
  const container = document.getElementById("cityFilters");
  const region = GEOGRAPHY.regions.find(r => r.name === state.selectedRegion);
  const department = region?.departments.find(d => d.name === state.selectedDepartment);
  const items = ["Tous"];
  if (department) {
    items.push(...department.cities);
  } else if (region) {
    region.departments.forEach(d => items.push(...d.cities));
  }

  container.innerHTML = items.map(label => `
    <button class="chip ${state.selectedCity === label ? "active" : ""}" data-kind="city" data-value="${escapeHtml(label)}">
      ${escapeHtml(label)}
    </button>
  `).join("");

  container.querySelectorAll(".chip").forEach(btn => {
    btn.addEventListener("click", () => {
      state.selectedCity = btn.dataset.value;
      renderFilters();
      renderCards();
    });
  });
}

function renderFilters() {
  buildThemeFilters();
  buildRegionFilters();
  buildDepartmentFilters();
  buildCityFilters();
}

function getFilteredItems() {
  return state.items.filter(item => {
    const searchMatch = !state.search || (
      (item.title && item.title.toLowerCase().includes(state.search)) ||
      (item.summary && item.summary.toLowerCase().includes(state.search)) ||
      (item.theme && item.theme.toLowerCase().includes(state.search)) ||
      (item.subtheme && item.subtheme.toLowerCase().includes(state.search)) ||
      (item.region && item.region.toLowerCase().includes(state.search)) ||
      (item.department && item.department.toLowerCase().includes(state.search)) ||
      (item.city && item.city.toLowerCase().includes(state.search))
    );

    const themeMatch = state.selectedTheme === "Tous" || item.theme === state.selectedTheme;
    const regionMatch = state.selectedRegion === "Tous" || item.region === state.selectedRegion;
    const departmentMatch = state.selectedDepartment === "Tous" || item.department === state.selectedDepartment;
    const cityMatch = state.selectedCity === "Tous" || item.city === state.selectedCity;

    return searchMatch && themeMatch && regionMatch && departmentMatch && cityMatch;
  });
}

function formatDate(dateString) {
  const d = new Date(dateString);
  if (isNaN(d)) return dateString;
  return d.toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function renderCards() {
  const cards = document.getElementById("cards");
  const filtered = getFilteredItems();

  cards.innerHTML = filtered.map(item => {
    const imageHtml = item.image ? `
      <div class="card-media">
        <img src="${escapeHtml(item.image)}" alt="" loading="lazy" onerror="this.onerror=null;this.src='assets/placeholder.svg';" />
      </div>` : '';

    return `
    <article class="card">
      ${imageHtml}
      <div class="card-top">
        <span class="badge">${escapeHtml(item.subtheme || item.theme || '')}</span>
        <span class="meta">${escapeHtml(formatDate(item.date))}</span>
      </div>

      <h3>${escapeHtml(item.title)}</h3>
      <p>${escapeHtml(item.summary)}</p>

      <div class="card-footer">
        <span>${escapeHtml([item.region, item.department, item.city].filter(Boolean).join(' / '))}</span>
        <a href="${escapeHtml(item.url || '#')}" target="_blank" rel="noreferrer">Voir</a>
      </div>
    </article>
  `}).join("");

  document.getElementById("countAlerts").textContent = String(filtered.length);
  document.getElementById("countThemes").textContent = String(new Set(filtered.map(item => item.theme)).size);
  document.getElementById("countRegions").textContent = String(new Set(filtered.map(item => item.region)).size);
}

async function loadData(isManualRefresh = false) {
  const target = "./data/veille.json";

  try {
    const response = await fetch(target, { cache: "no-store" });
    if (!response.ok) throw new Error("Data file not found");

    const data = await response.json();
    state.items = Array.isArray(data.items) ? data.items : fallbackItems;

    state.items = state.items.map(it => ({
      title: it.title || 'Sans titre',
      summary: it.summary || '',
      url: it.url || '#',
      date: it.date || new Date().toISOString(),
      theme: it.theme || it.category || 'Sécurité & Criminalité',
      subtheme: it.subtheme || it.subTheme || it.sub || '',
      region: it.region || '',
      department: it.department || '',
      city: it.city || '',
      image: it.image || null,
      source: it.source || ''
    }));

  } catch (error) {
    console.warn(error);
    state.items = fallbackItems;
  }

  renderCards();
  const now = new Date();
  document.getElementById("lastUpdate").textContent = "Dernière mise à jour : " + now.toLocaleString("fr-FR");
  if (isManualRefresh) {
    const btn = document.getElementById("refreshBtn");
    const old = btn.textContent;
    btn.textContent = "OK";
    setTimeout(() => {
      btn.textContent = old;
    }, 1200);
  }
}
