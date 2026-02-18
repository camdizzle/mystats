const $ = id => document.getElementById(id);
const leaderboard = $('leaderboard');
const boardTitle = document.querySelector('.board-title');
const headerPills = [
  $('stat-avg-today'),
  $('stat-uniq-today'),
  $('stat-races-today'),
  $('stat-avg-season'),
  $('stat-uniq-season'),
  $('stat-races-season'),
];
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
let refreshTimer = null;
let pillRotationTimer = null;
let viewFallbackTimer = null;
let activeViewIndex = 0;
let currentViews = [];
let lastRaceKey = null;
let top3ShowTimeout = null;
let top3IsShowing = false;
let activePillPage = 0;
let leaderboardScrollTimer = null;
let leaderboardScrollDirection = 1;
let leaderboardScrollPauseUntil = 0;
let leaderboardScrollRetryTimer = null;
let lastRenderedViewKey = null;
let hasHydratedOnce = false;

function clampNumber(value, min, max, fallback) {
  const num = Number(value);
  if (!Number.isFinite(num)) return fallback;
  return Math.min(max, Math.max(min, num));
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
  renderPillPage();
}

function renderPillPage() {
  const pillPageSize = 3;
  headerPills.forEach((pill, idx) => {
    if (!pill) return;
    const start = activePillPage * pillPageSize;
    const end = start + pillPageSize;
    pill.style.display = idx >= start && idx < end ? 'block' : 'none';
  });
}

function rotatePills() {
  const totalPages = Math.max(1, Math.ceil(headerPills.length / 3));
  if (totalPages <= 1) return;
  activePillPage = (activePillPage + 1) % totalPages;
  renderPillPage();
}

function startPillRotationTimer() {
  if (pillRotationTimer) clearInterval(pillRotationTimer);
  pillRotationTimer = setInterval(rotatePills, settings.rotationSeconds * 1000);
}

function stopViewFallbackTimer() {
  if (viewFallbackTimer) {
    clearTimeout(viewFallbackTimer);
    viewFallbackTimer = null;
  }
}

function scheduleViewFallbackAdvance() {
  stopViewFallbackTimer();
  if (top3IsShowing || currentViews.length <= 1) return;

  viewFallbackTimer = setTimeout(() => {
    advanceView();
  }, settings.rotationSeconds * 1000);
}

function stopLeaderboardAutoScroll() {
  if (leaderboardScrollTimer) {
    clearInterval(leaderboardScrollTimer);
    leaderboardScrollTimer = null;
  }
  if (leaderboardScrollRetryTimer) {
    clearTimeout(leaderboardScrollRetryTimer);
    leaderboardScrollRetryTimer = null;
  }
}

function advanceView() {
  if (top3IsShowing || currentViews.length <= 1) return;
  activeViewIndex = (activeViewIndex + 1) % currentViews.length;
  renderCurrentView(true);
}

function startLeaderboardAutoScroll() {
  stopLeaderboardAutoScroll();
  stopViewFallbackTimer();

  if (!leaderboard) return;
  const maxScrollTop = leaderboard.scrollHeight - leaderboard.clientHeight;
  if (maxScrollTop <= 2) {
    leaderboard.scrollTop = 0;
    scheduleViewFallbackAdvance();

    leaderboardScrollRetryTimer = setTimeout(() => {
      if (!top3IsShowing) startLeaderboardAutoScroll();
    }, 600);
    return;
  }

  leaderboard.scrollTop = 0;
  leaderboardScrollDirection = 1;
  leaderboardScrollPauseUntil = Date.now() + 1200;

  leaderboardScrollTimer = setInterval(() => {
    const currentMax = leaderboard.scrollHeight - leaderboard.clientHeight;
    if (currentMax <= 2) {
      stopLeaderboardAutoScroll();
      leaderboard.scrollTop = 0;
      scheduleViewFallbackAdvance();
      return;
    }

    const now = Date.now();
    if (now < leaderboardScrollPauseUntil) return;

    leaderboard.scrollTop += leaderboardScrollDirection * 1.4;

    if (leaderboardScrollDirection > 0 && leaderboard.scrollTop >= currentMax - 1) {
      leaderboard.scrollTop = currentMax;
      leaderboardScrollDirection = -1;
      leaderboardScrollPauseUntil = now + 1200;
      return;
    }

    if (leaderboardScrollDirection < 0 && leaderboard.scrollTop <= 1) {
      leaderboard.scrollTop = 0;
      leaderboardScrollPauseUntil = now + 900;
      advanceView();
    }
  }, 32);
}

function renderRows(rows) {
  document.body.classList.remove('top3-active');

  if (!rows?.length) {
    leaderboard.innerHTML = '<li>No race data yet.</li>';
    stopLeaderboardAutoScroll();
    stopViewFallbackTimer();
    return;
  }

  leaderboard.innerHTML = rows.map(r => {
    const emote = settings.showMedals ? getPlacementEmote(r.placement) : '';
    const decoratedName = emote ? `${emote} ${r.name}` : r.name;
    return `<li><span>#${r.placement}</span><span>${decoratedName}</span><span>${fmt(r.points)} pts</span></li>`;
  }).join('');
  setTimeout(startLeaderboardAutoScroll, 0);
}

function renderTop3Rows(rows) {
  document.body.classList.add('top3-active');
  stopLeaderboardAutoScroll();
  stopViewFallbackTimer();

  const safeRows = (rows || []).slice(0, 3);
  leaderboard.innerHTML = safeRows.map((r, idx) => {
    const medal = ['🥇', '🥈', '🥉'][idx] || getPlacementEmote(r.placement);
    return `
      <li class="top3-card top3-card--${idx + 1}">
        <span class="top3-rank">${medal} #${r.placement}</span>
        <span class="top3-name">${r.name}</span>
        <span class="top3-points">${fmt(r.points)} pts</span>
      </li>
    `;
  }).join('');
}

function ensureLeaderboardAutoScroll() {
  if (!leaderboard || top3IsShowing) return;
  if (!leaderboard.children.length) return;
  if (leaderboardScrollTimer || leaderboardScrollRetryTimer) return;
  startLeaderboardAutoScroll();
}

function getViewRenderKey(view) {
  if (!view) return 'empty';
  const rows = Array.isArray(view.rows) ? view.rows : [];
  const rowSignature = rows
    .map(row => `${row.placement}|${row.name}|${row.points}`)
    .join('||');

  return [
    view.id || '',
    view.title || '',
    settings.showMedals,
    rowSignature,
  ].join('::');
}

function renderCurrentView(force = false) {
  if (!currentViews.length) {
    if (boardTitle) boardTitle.textContent = 'Top Results';
    lastRenderedViewKey = 'empty';
    renderRows([]);
    return;
  }

  const safeIndex = Math.min(activeViewIndex, currentViews.length - 1);
  activeViewIndex = safeIndex;
  const view = currentViews[safeIndex];
  const nextRenderKey = getViewRenderKey(view);

  if (!force && nextRenderKey === lastRenderedViewKey) {
    return;
  }

  lastRenderedViewKey = nextRenderKey;
  if (boardTitle) boardTitle.textContent = view.title || 'Top Results';
  renderRows(view.rows || []);
}

function startRefreshTimer() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(refresh, settings.refreshSeconds * 1000);
}

function showTop3ForTenSeconds(top3View) {
  if (!top3View?.rows?.length) return;

  top3IsShowing = true;
  if (top3ShowTimeout) clearTimeout(top3ShowTimeout);

  if (boardTitle) boardTitle.textContent = top3View.title || '🔥 Latest Race Podium 🔥';
  renderTop3Rows(top3View.rows);

  top3ShowTimeout = setTimeout(() => {
    top3IsShowing = false;
    lastRenderedViewKey = null;
    renderCurrentView(true);
  }, 10000);
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
  if (rotationChanged) {
    startPillRotationTimer();
    scheduleViewFallbackAdvance();
  }
  if (refreshChanged) startRefreshTimer();
}

function syncViews(views = []) {
  const previousViewId = currentViews[activeViewIndex]?.id;
  currentViews = views;

  if (!currentViews.length) {
    activeViewIndex = 0;
    renderCurrentView(true);
    return;
  }

  if (previousViewId) {
    const previousIndex = currentViews.findIndex(v => v.id === previousViewId);
    activeViewIndex = previousIndex >= 0 ? previousIndex : 0;
  } else {
    activeViewIndex = Math.min(activeViewIndex, currentViews.length - 1);
  }

  if (!top3IsShowing) {
    renderCurrentView();
    ensureLeaderboardAutoScroll();
  }
}

async function refresh() {
  try {
    const r = await fetch('/api/overlay/top3', { cache: 'no-store' });
    const p = await r.json();

    $('overlay-title').textContent = p.title || 'MyStats Live Results';
    applyServerSettings(p.settings || {});
    updateHeaderStats(p.header_stats || {});
    syncViews(p.views || []);

    const raceKey = p.recent_race_top3?.race_key || null;
    if (!hasHydratedOnce) {
      hasHydratedOnce = true;
      lastRaceKey = raceKey;
      return;
    }

    if (raceKey && raceKey !== lastRaceKey) {
      lastRaceKey = raceKey;
      showTop3ForTenSeconds(p.recent_race_top3);
    }
  } catch (_error) {
  }
}

window.addEventListener('resize', ensureLeaderboardAutoScroll);

renderPillPage();
refresh();
startRefreshTimer();
startPillRotationTimer();
