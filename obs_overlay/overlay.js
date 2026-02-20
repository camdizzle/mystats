const $ = id => document.getElementById(id);
const leaderboard = $('leaderboard');
const boardShell = document.querySelector('.board-shell');
const splashScreen = $('splash-screen');
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
let currentViews = [];
let activePillPage = 0;
let leaderboardScrollTimer = null;
let leaderboardScrollPauseUntil = 0;
let leaderboardScrollRetryTimer = null;
let sectionAnchors = [];
let lastRenderedViewsKey = '';
let cycleRestartTimer = null;
let lastRaceKey = null;
let hasHydratedOnce = false;
let top3IsShowing = false;
let top3ShowTimeout = null;
const splashDurationMs = 5500;
const top3ShowDurationMs = 10000;

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
  const setPillValue = (id, value) => {
    const valueEl = document.querySelector(`#${id} .pill-value`);
    if (valueEl) valueEl.textContent = fmt(value);
  };

  setPillValue('stat-avg-today', s.avg_points_today);
  setPillValue('stat-uniq-today', s.unique_racers_today);
  setPillValue('stat-races-today', s.total_races_today);
  setPillValue('stat-avg-season', s.avg_points_season);
  setPillValue('stat-uniq-season', s.unique_racers_season);
  setPillValue('stat-races-season', s.total_races_season);
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

function clearCycleRestartTimer() {
  if (cycleRestartTimer) {
    clearTimeout(cycleRestartTimer);
    cycleRestartTimer = null;
  }
}

function showLeaderboardView() {
  if (boardShell) boardShell.classList.remove('is-hidden');
  document.body.classList.remove('top3-active');
  leaderboard?.classList.remove('is-top3-mode');
  if (splashScreen) {
    splashScreen.classList.remove('is-visible');
    splashScreen.setAttribute('aria-hidden', 'true');
    splashScreen.setAttribute('visible', 'false');
  }
}

function showSplashView() {
  if (!hasReachedEndOfStackedViews()) return;

  stopLeaderboardAutoScroll();
  if (boardShell) boardShell.classList.add('is-hidden');
  if (splashScreen) {
    splashScreen.classList.add('is-visible');
    splashScreen.setAttribute('aria-hidden', 'false');
    splashScreen.setAttribute('visible', 'true');
  }

  clearCycleRestartTimer();
  cycleRestartTimer = setTimeout(() => {
    showLeaderboardView();
    if (leaderboard) {
      leaderboard.scrollTop = 0;
      updateBoardTitleFromScroll();
    }
    startLeaderboardAutoScroll();
  }, splashDurationMs);
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

function updateBoardTitleFromScroll() {
  if (!sectionAnchors.length || !leaderboard || top3IsShowing) return;
}

function renderTop3Rows(rows = [], title = '🔥 Latest Race Podium 🔥') {
  if (!leaderboard) return;

  const safeRows = rows.slice(0, 3);
  document.body.classList.add('top3-active');
  leaderboard.classList.add('is-top3-mode');
  leaderboard.scrollTop = 0;

  const titleMarkup = `<li class="leaderboard-section-title" data-section-title="${escapeHtml(title)}">${escapeHtml(title)}</li>`;
  const cardsMarkup = safeRows.map((r, idx) => {
    const medal = ['🥇', '🥈', '🥉'][idx] || getPlacementEmote(r.placement);
    return `<li class="top3-card top3-card--${idx + 1}"><span class="top3-rank">${escapeHtml(medal)} #${escapeHtml(r.placement)}</span><span class="top3-name">${escapeHtml(r.name)}</span><span class="top3-points">${fmt(r.points)} pts</span></li>`;
  }).join('');

  leaderboard.innerHTML = `${titleMarkup}${cardsMarkup}`;
}

function showTop3ForTenSeconds(top3View) {
  if (!top3View?.rows?.length || top3IsShowing) return;

  top3IsShowing = true;
  const top3Title = top3View.title || '🔥 Latest Race Podium 🔥';
  stopLeaderboardAutoScroll();
  clearCycleRestartTimer();
  renderTop3Rows(top3View.rows, top3Title);

  if (top3ShowTimeout) clearTimeout(top3ShowTimeout);
  top3ShowTimeout = setTimeout(() => {
    top3IsShowing = false;
    document.body.classList.remove('top3-active');
    leaderboard?.classList.remove('is-top3-mode');
    lastRenderedViewsKey = '';
    renderCombinedRows(currentViews);
    ensureLeaderboardAutoScroll();
  }, top3ShowDurationMs);
}

function startLeaderboardAutoScroll() {
  if (top3IsShowing) return;
  stopLeaderboardAutoScroll();
  clearCycleRestartTimer();
  showLeaderboardView();

  if (!leaderboard) return;
  const maxScrollTop = leaderboard.scrollHeight - leaderboard.clientHeight;
  if (maxScrollTop <= 2) {
    leaderboard.scrollTop = 0;

    leaderboardScrollRetryTimer = setTimeout(() => {
      startLeaderboardAutoScroll();
    }, 600);
    return;
  }

  leaderboard.scrollTop = 0;
  leaderboardScrollPauseUntil = Date.now() + 1200;

  leaderboardScrollTimer = setInterval(() => {
    const currentMax = leaderboard.scrollHeight - leaderboard.clientHeight;
    if (currentMax <= 2) {
      stopLeaderboardAutoScroll();
      leaderboard.scrollTop = 0;
      return;
    }

    const now = Date.now();
    if (now < leaderboardScrollPauseUntil) return;

    leaderboard.scrollTop += 1.4;

    if (leaderboard.scrollTop >= currentMax - 1 && hasReachedEndOfStackedViews()) {
      leaderboard.scrollTop = currentMax;
      showSplashView();
    }
  }, 32);
}


function hasReachedEndOfStackedViews() {
  if (!leaderboard) return false;

  const finalRow = leaderboard.querySelector('.leaderboard-row--final');
  if (!finalRow) return false;

  const currentMax = leaderboard.scrollHeight - leaderboard.clientHeight;
  if (currentMax > 2 && leaderboard.scrollTop < currentMax - 10) return false;

  const listBounds = leaderboard.getBoundingClientRect();
  const finalRowBounds = finalRow.getBoundingClientRect();
  return finalRowBounds.bottom <= listBounds.bottom + 2;
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function getViewsRenderKey(views) {
  if (!Array.isArray(views)) return 'invalid';

  return views.map((view) => {
    const title = view?.title || '';
    const rows = Array.isArray(view?.rows) ? view.rows : [];
    const rowKey = rows
      .map((row) => `${row?.placement ?? ''}|${row?.name ?? ''}|${row?.points ?? ''}`)
      .join('||');
    return `${title}::${rowKey}`;
  }).join('@@');
}

function renderCombinedRows(views) {
  if (!leaderboard) return;
  showLeaderboardView();
  leaderboard.classList.remove('is-top3-mode');
  sectionAnchors = [];

  if (!Array.isArray(views) || !views.length) {
    leaderboard.innerHTML = '<li>No race data yet.</li>';
    stopLeaderboardAutoScroll();
    return;
  }

  const markup = views.map((view, viewIndex) => {
    const sectionTitle = view.title || 'Top Results';
    const rows = Array.isArray(view.rows) ? view.rows : [];
    const sectionTitleMarkup = `<li class="leaderboard-section-title" data-section-title="${escapeHtml(sectionTitle)}">${escapeHtml(sectionTitle)}</li>`;

    const rowMarkup = rows.map((r, rowIndex) => {
      const emote = settings.showMedals ? getPlacementEmote(r.placement) : '';
      const decoratedName = emote ? `${emote} ${r.name}` : r.name;
      const podiumClass = rowIndex < 3 ? ` leaderboard-row--podium-${rowIndex + 1}` : '';
      return `<li class="leaderboard-row${podiumClass}"><span class="row-rank">#${escapeHtml(r.placement)}</span><span>${escapeHtml(decoratedName)}</span><span>${fmt(r.points)} pts</span></li>`;
    }).join('');

    const gap = viewIndex > 0 ? '<li class="leaderboard-gap" aria-hidden="true"></li>' : '';
    return `${gap}${sectionTitleMarkup}${rowMarkup}`;
  }).join('');

  leaderboard.innerHTML = markup;

  const renderedRows = Array.from(leaderboard.querySelectorAll('.leaderboard-row'));
  renderedRows.forEach((row) => row.classList.remove('leaderboard-row--final'));
  const finalRenderedRow = renderedRows[renderedRows.length - 1];
  if (finalRenderedRow) {
    finalRenderedRow.classList.add('leaderboard-row--final');
  }

  sectionAnchors = Array.from(leaderboard.querySelectorAll('.leaderboard-section-title')).map((el) => ({
    title: el.dataset.sectionTitle || 'Top Results',
    offsetTop: el.offsetTop,
  }));

  updateBoardTitleFromScroll();
  setTimeout(ensureLeaderboardAutoScroll, 0);
}

function ensureLeaderboardAutoScroll() {
  if (top3IsShowing) return;
  if (!leaderboard) return;
  if (!leaderboard.children.length) return;
  if (leaderboardScrollTimer || leaderboardScrollRetryTimer) return;
  startLeaderboardAutoScroll();
}

function startRefreshTimer() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(refresh, settings.refreshSeconds * 1000);
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
  }
  if (refreshChanged) startRefreshTimer();
}

function syncViews(views = []) {
  currentViews = views;

  if (top3IsShowing) {
    return;
  }

  const nextRenderKey = `${settings.showMedals}::${getViewsRenderKey(currentViews)}`;

  if (nextRenderKey === lastRenderedViewsKey) {
    updateBoardTitleFromScroll();
    ensureLeaderboardAutoScroll();
    return;
  }

  lastRenderedViewsKey = nextRenderKey;
  renderCombinedRows(currentViews);
  ensureLeaderboardAutoScroll();
}

async function refresh() {
  try {
    const r = await fetch('/api/overlay/top3', { cache: 'no-store' });
    const p = await r.json();

    $('overlay-title').textContent = p.title || 'MyStats Live Results';
    applyServerSettings(p.settings || {});
    updateHeaderStats(p.header_stats || {});
    const normalizedViews = Array.isArray(p.views)
      ? p.views
      : [
          { id: 'season', title: 'Top 10 Season', rows: p.top10_season || [] },
          { id: 'today', title: 'Top 10 Today', rows: p.top10_today || [] },
          ...(Array.isArray(p.top10_previous_race) && p.top10_previous_race.length
            ? [{ id: 'previous', title: 'Top 10 Previous Race', rows: p.top10_previous_race }]
            : []),
        ];

    syncViews(normalizedViews);

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
  } catch (error) {
    console.error('Overlay refresh failed:', error);
    if (leaderboard) leaderboard.innerHTML = '<li>Unable to load race data.</li>';
    lastRenderedViewsKey = '';
    stopLeaderboardAutoScroll();
    clearCycleRestartTimer();
  }
}

window.addEventListener('resize', () => {
  sectionAnchors = Array.from(leaderboard?.querySelectorAll('.leaderboard-section-title') || []).map((el) => ({
    title: el.dataset.sectionTitle || 'Top Results',
    offsetTop: el.offsetTop,
  }));
  ensureLeaderboardAutoScroll();
  updateBoardTitleFromScroll();
});

leaderboard?.addEventListener('scroll', updateBoardTitleFromScroll);
showLeaderboardView();

renderPillPage();
refresh();
startRefreshTimer();
startPillRotationTimer();
