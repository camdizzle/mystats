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
  horizontalLayout: false,
};

const themes = {
  midnight: { text: '#eef3ff', muted: '#9bb5ff', accent: '#7fd8ff', panelBase: '10,14,27', panel2Base: '22,33,57' },
  ocean: { text: '#ecf8ff', muted: '#84d2ff', accent: '#78f1ff', panelBase: '4,24,35', panel2Base: '8,53,75' },
  sunset: { text: '#fff0fa', muted: '#ffb6d6', accent: '#ffc575', panelBase: '38,10,31', panel2Base: '81,20,63' },
  forest: { text: '#e9ffed', muted: '#9be6aa', accent: '#7afec3', panelBase: '9,25,19', panel2Base: '17,64,47' },
  mono: { text: '#f4f6ff', muted: '#c7cde4', accent: '#d2dcff', panelBase: '17,20,33', panel2Base: '40,46,72' },
  violethearts: { text: '#fff3ff', muted: '#f0b8ff', accent: '#9fd6ff', pointsAccent: '#ff4fd8', panelBase: '43,14,58', panel2Base: '121,41,148' },
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
let horizontalLoopWidth = 0;
let lastRaceKey = null;
let hasHydratedOnce = false;
let top3IsShowing = false;
let top3ShowTimeout = null;
const splashDurationMs = 5000;
const top3ShowDurationMs = 10000;

function clampNumber(value, min, max, fallback) {
  const num = Number(value);
  if (!Number.isFinite(num)) return fallback;
  return Math.min(max, Math.max(min, num));
}


function getDisplayName(row = {}, fallbackPlacement = null) {
  const invalidTokens = new Set(['', 'unknown', 'none', 'null', 'undefined', 'n/a', 'na']);
  const candidates = [
    row?.name,
    row?.display_name,
    row?.displayName,
    row?.username,
    row?.user,
    row?.racer,
    row?.player,
  ];

  for (const candidate of candidates) {
    const value = String(candidate ?? '').replace(/\s+/g, ' ').trim();
    if (!value) continue;
    if (invalidTokens.has(value.toLowerCase())) continue;
    return value;
  }

  if (fallbackPlacement !== null && fallbackPlacement !== undefined && fallbackPlacement !== '') {
    return `Racer #${fallbackPlacement}`;
  }
  return 'Unknown Racer';
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

function showSplashView(force = false) {
  if (settings.horizontalLayout) return;
  if (!force && !hasReachedEndOfStackedViews()) return;

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
      leaderboard.scrollLeft = 0;
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

function syncHorizontalLoopWidth() {
  if (!leaderboard || !settings.horizontalLayout) {
    horizontalLoopWidth = 0;
    return;
  }

  const loopBoundary = leaderboard.querySelector('.leaderboard-loop-boundary');
  horizontalLoopWidth = loopBoundary ? loopBoundary.offsetLeft : 0;
}

function renderTop3Rows(rows = [], title = '🔥 Latest Race Podium 🔥') {
  if (!leaderboard) return;

  const safeRows = rows.filter((row) => row?.finished !== false).slice(0, 3);
  document.body.classList.add('top3-active');
  leaderboard.classList.add('is-top3-mode');
  leaderboard.scrollTop = 0;

  const titleMarkup = `<li class="leaderboard-section-title" data-section-title="${escapeHtml(title)}">${escapeHtml(title)}</li>`;
  const cardsMarkup = [0, 1, 2].map((idx) => {
    const r = safeRows[idx];
    if (!r) return `<li class="top3-card top3-card--${idx + 1} is-hidden" aria-hidden="true"></li>`;
    const medal = ['🥇', '🥈', '🥉'][idx] || getPlacementEmote(r.placement);
    return `<li class="top3-card top3-card--${idx + 1}"><span class="top3-rank">${escapeHtml(medal)} #${escapeHtml(r.placement)}</span><span class="top3-name">${escapeHtml(getDisplayName(r, r.placement))}</span><span class="top3-points">${fmt(r.points)} pts</span></li>`;
  }).join('');

  leaderboard.innerHTML = `${titleMarkup}${cardsMarkup}`;
}

function showTop3ForTenSeconds(top3View) {
  if (settings.horizontalLayout) return;
  const finishedRows = (top3View?.rows || []).filter((row) => row?.finished !== false);
  if (!finishedRows.length || top3IsShowing) return;

  top3IsShowing = true;
  const top3Title = top3View.title || '🔥 Latest Race Podium 🔥';
  stopLeaderboardAutoScroll();
  clearCycleRestartTimer();
  renderTop3Rows(finishedRows, top3Title);

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
  const maxScroll = settings.horizontalLayout
    ? leaderboard.scrollWidth - leaderboard.clientWidth
    : leaderboard.scrollHeight - leaderboard.clientHeight;

  if (maxScroll <= 2) {
    leaderboard.scrollTop = 0;
    leaderboard.scrollLeft = 0;

    leaderboardScrollRetryTimer = setTimeout(() => {
      startLeaderboardAutoScroll();
    }, 600);
    return;
  }

  leaderboard.scrollTop = 0;
  leaderboard.scrollLeft = 0;
  leaderboardScrollPauseUntil = Date.now() + 1200;

  leaderboardScrollTimer = setInterval(() => {
    const currentMax = settings.horizontalLayout
      ? leaderboard.scrollWidth - leaderboard.clientWidth
      : leaderboard.scrollHeight - leaderboard.clientHeight;

    if (currentMax <= 2) {
      stopLeaderboardAutoScroll();
      leaderboard.scrollTop = 0;
      leaderboard.scrollLeft = 0;
      return;
    }

    const now = Date.now();
    if (now < leaderboardScrollPauseUntil) return;

    if (settings.horizontalLayout) {
      leaderboard.scrollLeft += 1.4;
      if (horizontalLoopWidth > 0 && leaderboard.scrollLeft >= horizontalLoopWidth) {
        leaderboard.scrollLeft -= horizontalLoopWidth;
      } else if (leaderboard.scrollLeft >= currentMax - 1) {
        leaderboard.scrollLeft = 0;
      }
      return;
    }

    leaderboard.scrollTop += 1.4;

    if (leaderboard.scrollTop >= currentMax - 1) {
      leaderboard.scrollTop = currentMax;

      if (hasReachedEndOfStackedViews()) {
        showSplashView();
      } else {
        leaderboardScrollPauseUntil = Date.now() + 800;
      }
    }
  }, 32);
}


function hasReachedEndOfStackedViews() {
  if (!leaderboard) return false;
  if (settings.horizontalLayout) return false;

  if (!hasScrolledIntoFinalSection()) return false;

  const finalRow = leaderboard.querySelector('.leaderboard-row--final');
  if (!finalRow) return false;

  const listBounds = leaderboard.getBoundingClientRect();
  const finalRowBounds = finalRow.getBoundingClientRect();
  return finalRowBounds.bottom <= listBounds.top + 2;
}

function hasScrolledIntoFinalSection() {
  if (!leaderboard) return false;
  if (!sectionAnchors.length) return false;
  if (sectionAnchors.length === 1) return true;

  const titles = leaderboard.querySelectorAll('.leaderboard-section-title');
  const lastTitle = titles[titles.length - 1];
  if (!lastTitle) return true;

  if (settings.horizontalLayout) {
    const liveOffsetLeft = lastTitle.offsetLeft;
    const viewportRight = leaderboard.scrollLeft + leaderboard.clientWidth;
    return viewportRight >= liveOffsetLeft + 20;
  }

  const liveOffsetTop = lastTitle.offsetTop;
  const viewportBottom = leaderboard.scrollTop + leaderboard.clientHeight;
  return viewportBottom >= liveOffsetTop + 20;
}

function syncEndSpacerHeight() {
  if (!leaderboard) return;
  const endSpacer = leaderboard.querySelector('.leaderboard-end-spacer');
  if (!endSpacer) return;
  if (settings.horizontalLayout) {
    endSpacer.style.width = `${leaderboard.clientWidth}px`;
    endSpacer.style.height = '1px';
    return;
  }
  endSpacer.style.height = `${leaderboard.clientHeight}px`;
  endSpacer.style.width = '1px';
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


function getRenderableViews(views = []) {
  if (!Array.isArray(views)) return [];
  return views.filter((view) => Array.isArray(view?.rows) && view.rows.length > 0);
}

function renderCombinedRows(views) {
  if (!leaderboard) return;
  showLeaderboardView();
  leaderboard.classList.remove('is-top3-mode');
  sectionAnchors = [];
  const previousScrollTop = leaderboard.scrollTop;
  const previousScrollLeft = leaderboard.scrollLeft;
  const renderableViews = getRenderableViews(views);

  if (!renderableViews.length) {
    leaderboard.innerHTML = '<li>No race data yet.</li>';
    stopLeaderboardAutoScroll();
    if (!settings.horizontalLayout) showSplashView(true);
    return;
  }

  const markup = renderableViews.map((view, viewIndex) => {
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

  const loopMessageMarkup = '<li class="leaderboard-loop-message">!mystats, !commands</li>';
  const firstCycleMarkup = `${markup}<li class="leaderboard-gap" aria-hidden="true"></li>${loopMessageMarkup}`;
  leaderboard.innerHTML = settings.horizontalLayout
    ? `${firstCycleMarkup}<li class="leaderboard-loop-boundary" aria-hidden="true"></li>${firstCycleMarkup}`
    : `${markup}<li class="leaderboard-end-spacer" aria-hidden="true"></li>`;

  syncEndSpacerHeight();
  syncHorizontalLoopWidth();

  const maxScrollTop = Math.max(0, leaderboard.scrollHeight - leaderboard.clientHeight);
  const maxScrollLeft = Math.max(0, leaderboard.scrollWidth - leaderboard.clientWidth);
  const scrollerIsActive = Boolean(leaderboardScrollTimer || leaderboardScrollRetryTimer);
  if (!scrollerIsActive && settings.horizontalLayout && previousScrollLeft > 0 && maxScrollLeft > 0) {
    leaderboard.scrollLeft = Math.min(previousScrollLeft, maxScrollLeft);
  }
  if (!scrollerIsActive && !settings.horizontalLayout && previousScrollTop > 0 && maxScrollTop > 0) {
    leaderboard.scrollTop = Math.min(previousScrollTop, maxScrollTop);
  }

  const renderedRows = Array.from(leaderboard.querySelectorAll('.leaderboard-row'));
  renderedRows.forEach((row) => row.classList.remove('leaderboard-row--final'));
  const finalRenderedRow = renderedRows[renderedRows.length - 1];
  if (finalRenderedRow) {
    finalRenderedRow.classList.add('leaderboard-row--final');
  }

  sectionAnchors = Array.from(leaderboard.querySelectorAll('.leaderboard-section-title')).map((el) => ({
    title: el.dataset.sectionTitle || 'Top Results',
    offsetTop: el.offsetTop,
    offsetLeft: el.offsetLeft,
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
  rootStyle.setProperty('--points-accent', theme.pointsAccent || theme.accent);
  rootStyle.setProperty('--panel', `rgba(${theme.panelBase}, ${settings.cardOpacity / 100})`);
  rootStyle.setProperty('--panel-2', `rgba(${theme.panel2Base}, ${Math.min(0.92, settings.cardOpacity / 100 + 0.08)})`);
  rootStyle.setProperty('--text-scale', String(settings.textScale / 100));
  document.body.classList.toggle('theme-violethearts', settings.theme === 'violethearts');
  document.body.classList.toggle('compact-rows', settings.compactRows);
  document.body.classList.toggle('horizontal-layout', settings.horizontalLayout);
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
    horizontalLayout: String(raw.horizontal_layout).toLowerCase() === 'true',
  };

  const rotationChanged = next.rotationSeconds !== settings.rotationSeconds;
  const refreshChanged = next.refreshSeconds !== settings.refreshSeconds;

  settings = next;
  applyTheme();
  renderPillPage();
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

  const renderableViews = getRenderableViews(currentViews);
  const nextRenderKey = `${settings.showMedals}::${settings.horizontalLayout}::${getViewsRenderKey(renderableViews)}`;

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
    const shouldShowPreviousRace = Array.isArray(p.top10_previous_race)
      && p.top10_previous_race.length;

    const normalizedViews = Array.isArray(p.views)
      ? p.views
      : [
          { id: 'season', title: 'Top 10 Season', rows: p.top10_season || [] },
          { id: 'today', title: 'Top 10 Today', rows: p.top10_today || [] },
          ...(shouldShowPreviousRace
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
  syncEndSpacerHeight();
  syncHorizontalLoopWidth();
  sectionAnchors = Array.from(leaderboard?.querySelectorAll('.leaderboard-section-title') || []).map((el) => ({
    title: el.dataset.sectionTitle || 'Top Results',
    offsetTop: el.offsetTop,
    offsetLeft: el.offsetLeft,
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
