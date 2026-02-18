const $ = id => document.getElementById(id);
const leaderboard = $('leaderboard');
const fmt = n => new Intl.NumberFormat().format(n || 0);

const defaultSettings = {
  rotationSeconds: 10,
  refreshSeconds: 3,
  theme: 'midnight',
  cardOpacity: 84,
  textScale: 100,
  showMedals: true,
  compactRows: false,
};

const themes = {
  midnight: { text: '#eef3ff', muted: '#9bb5ff', accent: '#7fd8ff', panelBase: '10,14,27', panel2Base: '22,33,57' },
  ocean: { text: '#ecf8ff', muted: '#84d2ff', accent: '#78f1ff', panelBase: '4,24,35', panel2Base: '8,53,75' },
  sunset: { text: '#fff0fa', muted: '#ffb6d6', accent: '#ffc575', panelBase: '38,10,31', panel2Base: '81,20,63' },
  forest: { text: '#e9ffed', muted: '#9be6aa', accent: '#7afec3', panelBase: '9,25,19', panel2Base: '17,64,47' },
  mono: { text: '#f4f6ff', muted: '#c7cde4', accent: '#d2dcff', panelBase: '17,20,33', panel2Base: '40,46,72' },
};

let settings = { ...defaultSettings };
let statsMode = 'today';
let rotationTimer = null;
let refreshTimer = null;

function clampNumber(value, min, max, fallback) {
  const num = Number(value);
  if (!Number.isFinite(num)) return fallback;
  return Math.min(max, Math.max(min, num));
}

function setStatsMode(mode) {
  statsMode = mode;
  document.querySelectorAll('.pill--today').forEach(el => {
    el.style.display = mode === 'today' ? 'block' : 'none';
  });
  document.querySelectorAll('.pill--season').forEach(el => {
    el.style.display = mode === 'season' ? 'block' : 'none';
  });
}

function toggleStatsMode() {
  setStatsMode(statsMode === 'today' ? 'season' : 'today');
}

function startRotationTimer() {
  if (rotationTimer) clearInterval(rotationTimer);
  rotationTimer = setInterval(toggleStatsMode, settings.rotationSeconds * 1000);
}

function startRefreshTimer() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(refresh, settings.refreshSeconds * 1000);
}

function getPlacementEmote(placement) {
  if (String(placement) === '1') return '🥇';
  if (String(placement) === '2') return '🥈';
  if (String(placement) === '3') return '🥉';
  return '';
}

function updateHeaderStats(s = {}) {
  $('stat-avg-today').textContent = `Avg Pts Today: ${fmt(s.avg_points_today)}`;
  $('stat-uniq-today').textContent = `Unique Racers Today: ${fmt(s.unique_racers_today)}`;
  $('stat-races-today').textContent = `Total Races Today: ${fmt(s.total_races_today)}`;
  $('stat-avg-season').textContent = `Avg Pts Season: ${fmt(s.avg_points_season)}`;
  $('stat-uniq-season').textContent = `Unique Racers Season: ${fmt(s.unique_racers_season)}`;
  $('stat-races-season').textContent = `Total Races Season: ${fmt(s.total_races_season)}`;
}

function renderRows(rows) {
  if (!rows?.length) {
    leaderboard.innerHTML = '<li>No race data yet.</li>';
    return;
  }
  leaderboard.innerHTML = rows.map(r => {
    const emote = settings.showMedals ? getPlacementEmote(r.placement) : '';
    const decoratedName = emote ? `${emote} ${r.name}` : r.name;
    return `<li><span>#${r.placement}</span><span>${decoratedName}</span><span>${fmt(r.points)} pts</span></li>`;
  }).join('');
}

function applyTheme() {
  const theme = themes[settings.theme] || themes.midnight;
  const rootStyle = document.documentElement.style;
  rootStyle.setProperty('--text', theme.text);
  rootStyle.setProperty('--muted', theme.muted);
  rootStyle.setProperty('--accent', theme.accent);
  rootStyle.setProperty('--panel', `rgba(${theme.panelBase}, ${settings.cardOpacity / 100})`);
  rootStyle.setProperty('--panel-2', `rgba(${theme.panel2Base}, ${Math.min(0.92, settings.cardOpacity / 100 + 0.08)})`);
  rootStyle.setProperty('--text-scale', String(settings.textScale / 100));
  document.body.classList.toggle('compact-rows', settings.compactRows);
}

function applyServerSettings(raw = {}) {
  const next = {
    rotationSeconds: clampNumber(raw.rotation_seconds, 3, 120, defaultSettings.rotationSeconds),
    refreshSeconds: clampNumber(raw.refresh_seconds, 1, 60, defaultSettings.refreshSeconds),
    theme: themes[raw.theme] ? raw.theme : defaultSettings.theme,
    cardOpacity: clampNumber(raw.card_opacity, 65, 100, defaultSettings.cardOpacity),
    textScale: clampNumber(raw.text_scale, 90, 125, defaultSettings.textScale),
    showMedals: String(raw.show_medals).toLowerCase() !== 'false',
    compactRows: String(raw.compact_rows).toLowerCase() === 'true',
  };

  const rotationChanged = next.rotationSeconds !== settings.rotationSeconds;
  const refreshChanged = next.refreshSeconds !== settings.refreshSeconds;

  settings = next;
  applyTheme();
  if (rotationChanged) startRotationTimer();
  if (refreshChanged) startRefreshTimer();
}

async function refresh() {
  try {
    const r = await fetch('/api/overlay/top3', { cache: 'no-store' });
    const p = await r.json();
    $('overlay-title').textContent = 'MyStats Live Results';
    applyServerSettings(p.settings || {});
    updateHeaderStats(p.header_stats || {});
    renderRows(p.rows || []);
  } catch (_error) {
  }
}

setStatsMode('today');
refresh();
startRefreshTimer();
startRotationTimer();
