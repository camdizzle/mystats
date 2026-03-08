const $ = id => document.getElementById(id);
const leaderboard = $('leaderboard');
const boardShell = document.querySelector('.board-shell');
const splashScreen = $('splash-screen');
const headerPillGroups = {
  today: [
    $('stat-avg-today'),
    $('stat-uniq-today'),
    $('stat-races-today'),
  ],
  season: [
    $('stat-avg-season'),
    $('stat-uniq-season'),
    $('stat-races-season'),
  ],
  br: [
    $('stat-br-avg-today'),
    $('stat-br-racers-today'),
    $('stat-br-total-today'),
  ],
};
const fmt = n => new Intl.NumberFormat().format(n || 0);


const activeSplashVariant = 'countdown';
document.body.dataset.splashVariant = activeSplashVariant;

let currentLanguage = 'en';
const I18N = {
  en: {},
  es: {
    'MyStats Live Results': 'MyStats Resultados en vivo',
    'MyStats Tilt Run Tracker': 'MyStats Seguimiento de Tilt',
    'WORLD RECORD!': '¡RÉCORD MUNDIAL!',
    'Avg Points Today': 'Promedio hoy',
    'All Racers Today': 'Todos hoy',
    'Total Races Today': 'Carreras hoy',
    'Avg Points Season': 'Promedio temporada',
    'All Racers Season': 'Todos temporada',
    'Total Races Season': 'Carreras temporada',
    'Avg Pts Per BR': 'Promedio por BR',
    'BR Racers Today': 'Jugadores BR hoy',
    'Total BRs Today': 'BR totales hoy',
    'set a new world record!': 'logró un nuevo récord mundial!',
    'Beat previous by': 'Superó al anterior por',
    'Active': 'Activo',
    'Idle': 'Inactivo',
    'No active run standings yet.': 'Aún no hay posiciones de la partida activa.',
    'No completed tilt run yet.': 'Aún no hay una partida tilt completada.',
  },
  au: {
    'MyStats Live Results': 'MyStats Live Ripper Results',
    'MyStats Tilt Run Tracker': 'MyStats Tilt Run Tracker, cobber',
    'WORLD RECORD!': 'WORLD RIPPER RECORD!',
    'Avg Points Today': 'Average Points Today, fair dinkum',
    'All Racers Today': 'All Mates Racing Today',
    'Total Races Today': 'Total Races Today, no worries',
    'Avg Points Season': 'Average Points This Season',
    'All Racers Season': 'All Mates This Season',
    'Total Races Season': 'Total Seasonal Races, strewth',
    'Avg Pts Per BR': 'Average BR Points Today',
    'BR Racers Today': 'BR Mates Today',
    'Total BRs Today': 'Total BRs Today, no worries',
    'set a new world record!': 'set a new world ripper record!',
    'Beat previous by': 'Beat the old mark by',
    'Active': 'Flat Out',
    'Idle': 'Taking a Breather',
    'No active run standings yet.': 'No active run standings yet, still warming up.',
    'No completed tilt run yet.': 'No completed tilt run yet, hang tight.',
  },
};
const AUSSIE_SLANG_REPLACEMENTS = [
  ['thank you', 'cheers'],
  ['thanks', 'cheers'],
  ['friend', 'mate'],
  ['friends', 'mates'],
  ['everyone', 'all the mates'],
  ['great', 'bonza'],
  ['very', 'bloody'],
  ['really', 'bloody'],
  ['goodbye', 'hooroo'],
  ['good', 'bonza'],
  ['active', 'flat out'],
  ['idle', 'taking a breather'],
  ['world record', 'world ripper record'],
];

function toAussieSlang(text) {
  let slang = String(text ?? '');
  AUSSIE_SLANG_REPLACEMENTS
    .sort((a, b) => b[0].length - a[0].length)
    .forEach(([source, target]) => {
      const pattern = new RegExp(`\\b${source.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&')}\\b`, 'gi');
      slang = slang.replace(pattern, target);
    });

  slang = slang.replace(/\s+/g, ' ').trim();
  if (!slang) return 'mate';
  if (!/\bmate\b[.!?]*$/i.test(slang)) {
    slang = slang.replace(/[.!?]+$/, '').trim();
    slang = `${slang}, mate`;
  }
  return slang;
}

const t = (k) => {
  const translated = I18N[currentLanguage]?.[k] || k;
  return currentLanguage === 'au' ? toAussieSlang(translated) : translated;
};

const defaultSettings = {
  rotationSeconds: 10,
  refreshSeconds: 3,
  theme: 'midnight',
  cardOpacity: 84,
  textScale: 100,
  showMedals: true,
  compactRows: false,
  horizontalLayout: false,
  horizontalFeedSeason: true,
  horizontalFeedToday: true,
  horizontalFeedRacesSeason: true,
  horizontalFeedBrsSeason: true,
  horizontalFeedRacesToday: true,
  horizontalFeedBrsToday: true,
  horizontalFeedPreviousRace: true,
  horizontalFeedEvents: true,
  horizontalFeedTiltCurrent: true,
  horizontalFeedTiltToday: true,
  horizontalFeedTiltSeason: true,
  horizontalFeedTiltLastRun: true,
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
let currentPillMode = 'race';
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
let recordOverlayTimeout = null;
let overlayEventActive = false;
let overlayEventTimeout = null;
let queuedRaceTop3 = null;
let overlayEventQueue = [];
let narrativeEventQueue = [];
let lastOverlayEventId = 0;
let hasHydratedOverlayEvents = false;
let currentResultsMode = '';
let currentSceneMode = 'pre-game';
let lastSceneMode = '';
let lastSplashAtMs = 0;
let cycleCountSinceSplash = 0;
const splashAnimationDurationMs = 9000;
const splashPostAnimationHoldMs = 1000;
const splashDurationMs = splashAnimationDurationMs + splashPostAnimationHoldMs;
const recordOverlayDurationMs = 5000;
const top3ShowDurationMs = 10000;
const eventOverlayDurationMs = 6500;
const minCyclesBetweenSplash = 5;
const minMsBetweenSplashes = 90000;

const recordOverlay = $('record-overlay');
const recordOverlayMessage = $('record-overlay-message');
const recordOverlayDelta = $('record-overlay-delta');
const eventOverlay = $('event-overlay');
const eventOverlayType = $('event-overlay-type');
const eventOverlayMessage = $('event-overlay-message');

function formatDurationDelta(secondsRaw) {
  const total = Number(secondsRaw);
  if (!Number.isFinite(total) || total <= 0) return '0.000s';
  if (total >= 60) {
    const minutes = Math.floor(total / 60);
    const seconds = total % 60;
    return `${minutes}:${seconds.toFixed(3).padStart(6, '0')}`;
  }
  return `${total.toFixed(3)}s`;
}

function hideRecordOverlay() {
  if (boardShell) boardShell.classList.remove('is-hidden');
  if (!recordOverlay) return;
  recordOverlay.classList.remove('is-visible');
  recordOverlay.setAttribute('aria-hidden', 'true');
}

function hideEventOverlay() {
  overlayEventActive = false;
  if (overlayEventTimeout) {
    clearTimeout(overlayEventTimeout);
    overlayEventTimeout = null;
  }
  if (boardShell) boardShell.classList.remove('is-hidden');
  if (!eventOverlay) return;
  eventOverlay.classList.remove('is-visible');
  eventOverlay.setAttribute('aria-hidden', 'true');
}

function showEventOverlay(eventPayload = {}) {
  if (settings.horizontalLayout) return;
  const type = String(eventPayload?.type || 'event').replace(/[_-]+/g, ' ').trim() || 'event';
  const message = String(eventPayload?.message || '').trim();
  if (!message) return;

  if (eventOverlayType) eventOverlayType.textContent = type.toUpperCase();
  if (eventOverlayMessage) eventOverlayMessage.textContent = message;
  if (boardShell) boardShell.classList.add('is-hidden');
  if (eventOverlay) {
    eventOverlay.classList.add('is-visible');
    eventOverlay.setAttribute('aria-hidden', 'false');
  }
  overlayEventActive = true;
}

function resolveSceneMode(payload = {}, overlayMode = '') {
  if (overlayMode === 'tilt') return 'tilt';

  const recentRace = payload?.recent_race_top3 || {};
  const raceRows = Array.isArray(recentRace?.rows) ? recentRace.rows : [];
  const raceType = normalizeRaceType(recentRace?.race_type);
  const isRecentRace = Boolean(recentRace?.race_timestamp || recentRace?.race_key);

  if (!raceRows.length) return 'pre-game';
  if (isRecentRace && raceType === 'br') return 'br';
  if (isRecentRace && raceType === 'race') return 'race';
  return 'post-race';
}

function shouldShowSplashInterstitial() {
  if (settings.horizontalLayout) return false;
  if (overlayEventQueue.length || narrativeEventQueue.length || queuedRaceTop3) return false;
  if (cycleCountSinceSplash < minCyclesBetweenSplash) return false;
  return (Date.now() - lastSplashAtMs) >= minMsBetweenSplashes;
}

function maybeShowCycleInterstitial() {
  if (settings.horizontalLayout) {
    leaderboardScrollPauseUntil = Date.now() + 800;
    return;
  }

  cycleCountSinceSplash += 1;
  processOverlayPresentationQueue();

  if (top3IsShowing || overlayEventActive) return;

  if (shouldShowSplashInterstitial()) {
    lastSplashAtMs = Date.now();
    cycleCountSinceSplash = 0;
    showSplashView();
    return;
  }

  leaderboardScrollPauseUntil = Date.now() + 900;
}

function processOverlayPresentationQueue() {
  if (settings.horizontalLayout) return;
  if (top3IsShowing || overlayEventActive) return;

  if (narrativeEventQueue.length) {
    const nextNarrative = narrativeEventQueue.shift();
    showEventOverlay(nextNarrative);
    if (overlayEventTimeout) clearTimeout(overlayEventTimeout);
    overlayEventTimeout = setTimeout(() => {
      hideEventOverlay();
      showLeaderboardView();
      ensureLeaderboardAutoScroll();
      processOverlayPresentationQueue();
    }, eventOverlayDurationMs);
    return;
  }

  if (overlayEventQueue.length) {
    const nextEvent = overlayEventQueue.shift();
    showEventOverlay(nextEvent);
    if (overlayEventTimeout) clearTimeout(overlayEventTimeout);
    overlayEventTimeout = setTimeout(() => {
      hideEventOverlay();
      showLeaderboardView();
      ensureLeaderboardAutoScroll();
      processOverlayPresentationQueue();
    }, eventOverlayDurationMs);
    return;
  }

  if (queuedRaceTop3) {
    const pendingTop3 = queuedRaceTop3;
    queuedRaceTop3 = null;
    showTop3ForTenSeconds(pendingTop3);
  }
}

function queueNarrativeEvent(eventPayload = {}) {
  if (settings.horizontalLayout) return;
  const message = String(eventPayload?.message || '').trim();
  if (!message) return;

  narrativeEventQueue.push({
    id: Number(eventPayload?.id || 0),
    type: String(eventPayload?.type || 'narrative').trim() || 'narrative',
    message,
  });
}

function queueOverlayEvent(eventPayload = {}) {
  if (settings.horizontalLayout) return;
  const message = String(eventPayload?.message || '').trim();
  if (!message) return;
  overlayEventQueue.push(eventPayload);
}

function queueTop3Overlay(top3View = {}) {
  if (settings.horizontalLayout) return;
  const finishedRows = (top3View?.rows || []).filter((row) => row?.finished !== false);
  if (!finishedRows.length) return;
  queuedRaceTop3 = top3View;
  processOverlayPresentationQueue();
}

function showRecordOverlay(top3View = {}) {
  const holderName = getDisplayName({
    name: top3View?.record_holder_name,
    display_name: top3View?.record_holder_name,
  }, 1);
  const beatBy = formatDurationDelta(top3View?.record_delta_seconds);

  if (recordOverlayMessage) {
    recordOverlayMessage.textContent = `${holderName} ${t('set a new world record!')}`;
  }
  if (recordOverlayDelta) {
    recordOverlayDelta.textContent = `${t('Beat previous by')} ${beatBy}`;
  }
  if (boardShell) boardShell.classList.add('is-hidden');
  if (recordOverlay) {
    recordOverlay.classList.add('is-visible');
    recordOverlay.setAttribute('aria-hidden', 'false');
  }
}

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
  setPillValue('stat-br-avg-today', s.br_avg_points_today);
  setPillValue('stat-br-racers-today', s.br_racers_today);
  setPillValue('stat-br-total-today', s.total_brs_today);
  renderPillPage();
}

function getPillPagesForMode() {
  return currentPillMode === 'br'
    ? [headerPillGroups.today, headerPillGroups.br]
    : [headerPillGroups.today, headerPillGroups.season];
}

function renderPillPage() {
  const allPills = [...headerPillGroups.today, ...headerPillGroups.season, ...headerPillGroups.br];
  allPills.forEach((pill) => {
    if (pill) pill.style.display = 'none';
  });

  const pages = getPillPagesForMode();
  const activePage = pages[activePillPage] || pages[0] || [];
  activePage.forEach((pill) => {
    if (pill) pill.style.display = 'block';
  });
}

function rotatePills() {
  const totalPages = Math.max(1, getPillPagesForMode().length);
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
  hideRecordOverlay();
  hideEventOverlay();
  document.body.classList.remove('top3-active');
  leaderboard?.classList.remove('is-top3-mode');
  if (splashScreen) {
    splashScreen.classList.remove('is-visible');
    splashScreen.classList.remove('splash-animate');
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
    splashScreen.classList.remove('splash-animate');
    void splashScreen.offsetWidth;
    splashScreen.classList.add('splash-animate');
    splashScreen.setAttribute('aria-hidden', 'false');
    splashScreen.setAttribute('visible', 'true');
  }

  clearCycleRestartTimer();
  cycleRestartTimer = setTimeout(() => {
    lastRenderedViewsKey = '';
    renderCombinedRows(currentViews);
    processOverlayPresentationQueue();
  }, splashDurationMs);
}

function isSplashViewActive() {
  return Boolean(splashScreen?.getAttribute('visible') === 'true');
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

  const startPodiumView = () => {
    hideRecordOverlay();
    renderTop3Rows(finishedRows, top3Title);

    if (top3ShowTimeout) clearTimeout(top3ShowTimeout);
    top3ShowTimeout = setTimeout(() => {
      top3IsShowing = false;
      document.body.classList.remove('top3-active');
      leaderboard?.classList.remove('is-top3-mode');
      lastRenderedViewsKey = '';
      renderCombinedRows(currentViews);
      ensureLeaderboardAutoScroll();
      processOverlayPresentationQueue();
    }, top3ShowDurationMs);
  };

  if (top3View?.is_record_race) {
    showRecordOverlay(top3View);
    if (recordOverlayTimeout) clearTimeout(recordOverlayTimeout);
    recordOverlayTimeout = setTimeout(startPodiumView, recordOverlayDurationMs);
    return;
  }

  startPodiumView();
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

    maybeShowCycleInterstitial();

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
        maybeShowCycleInterstitial();
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

  const endSpacer = leaderboard.querySelector('.leaderboard-end-spacer');
  if (!endSpacer) return false;

  const listBounds = leaderboard.getBoundingClientRect();
  const endSpacerBounds = endSpacer.getBoundingClientRect();
  return endSpacerBounds.top <= listBounds.top + 2;
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
    const isRecordRaceView = String(view?.id || '').toLowerCase() === 'previous' && view?.is_record_race;

    const rowMarkup = rows.map((r, rowIndex) => {
      if (r?.is_ticker_event) {
        const eventType = String(r?.event_type || 'event').replace(/[_-]+/g, ' ').toUpperCase();
        return `<li class="leaderboard-row leaderboard-row--event"><span class="row-rank">EVENT</span><span>${escapeHtml(r.name || '')}</span><span>${escapeHtml(eventType)}</span></li>`;
      }
      const emote = settings.showMedals ? getPlacementEmote(r.placement) : '';
      const isTeamView = String(view?.id || '').startsWith('teams-');
      const teamIcon = isTeamView ? String(r?.icon || '').trim() : '';
      const decoratedName = teamIcon
        ? `${teamIcon} ${r.name}`
        : (emote ? `${emote} ${r.name}` : r.name);
      const podiumClass = rowIndex < 3 ? ` leaderboard-row--podium-${rowIndex + 1}` : '';
      const recordClass = isRecordRaceView ? ' leaderboard-row--record-race' : '';
      return `<li class="leaderboard-row${podiumClass}${recordClass}"><span class="row-rank">#${escapeHtml(r.placement)}</span><span>${escapeHtml(decoratedName)}</span><span>${fmt(r.points)} pts</span></li>`;
    }).join('');

    const gap = viewIndex > 0 ? '<li class="leaderboard-gap" aria-hidden="true"></li>' : '';
    return `${gap}${sectionTitleMarkup}${rowMarkup}`;
  }).join('');

  const loopMessageMarkup = '<li class="leaderboard-loop-message">!mystats !commands</li>';
  const firstCycleMarkup = `${markup}<li class="leaderboard-gap" aria-hidden="true"></li>${loopMessageMarkup}`;
  if (settings.horizontalLayout) {
    const renderHorizontalCycles = (count) => {
      const loopBlock = firstCycleMarkup.repeat(count);
      leaderboard.innerHTML = `${loopBlock}<li class="leaderboard-loop-boundary" aria-hidden="true"></li>${loopBlock}`;
    };

    renderHorizontalCycles(1);
    syncEndSpacerHeight();
    syncHorizontalLoopWidth();

    if (horizontalLoopWidth > 0 && horizontalLoopWidth <= leaderboard.clientWidth + 8) {
      const targetWidth = leaderboard.clientWidth + 80;
      const repeatCount = Math.min(8, Math.max(2, Math.ceil(targetWidth / horizontalLoopWidth) + 1));
      renderHorizontalCycles(repeatCount);
    }
  } else {
    leaderboard.innerHTML = `${markup}<li class="leaderboard-end-spacer" aria-hidden="true"></li>`;
  }

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

function filterViewsForHorizontalFeed(views = [], overlayEvents = []) {
  const enabledById = {
    season: settings.horizontalFeedSeason,
    today: settings.horizontalFeedToday,
    'races-season': settings.horizontalFeedRacesSeason,
    'brs-season': settings.horizontalFeedBrsSeason,
    'races-today': settings.horizontalFeedRacesToday,
    'brs-today': settings.horizontalFeedBrsToday,
    previous: settings.horizontalFeedPreviousRace,
    'tilt-current': settings.horizontalFeedTiltCurrent,
    'tilt-today': settings.horizontalFeedTiltToday,
    'tilt-season': settings.horizontalFeedTiltSeason,
    'tilt-last-run': settings.horizontalFeedTiltLastRun,
  };

  const selectedViews = (Array.isArray(views) ? views : []).filter((view) => {
    const viewId = String(view?.id || '');
    if (!(viewId in enabledById)) return true;
    return Boolean(enabledById[viewId]);
  });

  if (settings.horizontalFeedEvents && Array.isArray(overlayEvents) && overlayEvents.length) {
    selectedViews.push({
      id: 'overlay-events',
      title: 'Ticker Events',
      rows: overlayEvents.slice(-20).map((eventItem, index) => ({
        placement: index + 1,
        name: eventItem?.message || '',
        points: 0,
        is_ticker_event: true,
        event_type: eventItem?.type || 'event',
      })),
    });
  }

  return selectedViews;
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
  currentLanguage = String(raw.language || currentLanguage || 'en').toLowerCase();
  const next = {
    rotationSeconds: clampNumber(raw.rotation_seconds, 3, 120, defaultSettings.rotationSeconds),
    refreshSeconds: clampNumber(raw.refresh_seconds, 1, 60, defaultSettings.refreshSeconds),
    theme: themes[raw.theme] ? raw.theme : defaultSettings.theme,
    cardOpacity: clampNumber(raw.card_opacity, 65, 100, defaultSettings.cardOpacity),
    textScale: clampNumber(raw.text_scale, 75, 175, defaultSettings.textScale),
    showMedals: String(raw.show_medals).toLowerCase() !== 'false',
    compactRows: String(raw.compact_rows).toLowerCase() === 'true',
    horizontalLayout: String(raw.horizontal_layout).toLowerCase() === 'true',
    horizontalFeedSeason: String(raw.horizontal_feed_season).toLowerCase() !== 'false',
    horizontalFeedToday: String(raw.horizontal_feed_today).toLowerCase() !== 'false',
    horizontalFeedRacesSeason: String(raw.horizontal_feed_races_season).toLowerCase() !== 'false',
    horizontalFeedBrsSeason: String(raw.horizontal_feed_brs_season).toLowerCase() !== 'false',
    horizontalFeedRacesToday: String(raw.horizontal_feed_races_today).toLowerCase() !== 'false',
    horizontalFeedBrsToday: String(raw.horizontal_feed_brs_today).toLowerCase() !== 'false',
    horizontalFeedPreviousRace: String(raw.horizontal_feed_previous_race).toLowerCase() !== 'false',
    horizontalFeedEvents: String(raw.horizontal_feed_events).toLowerCase() !== 'false',
    horizontalFeedTiltCurrent: String(raw.horizontal_feed_tilt_current).toLowerCase() !== 'false',
    horizontalFeedTiltToday: String(raw.horizontal_feed_tilt_today).toLowerCase() !== 'false',
    horizontalFeedTiltSeason: String(raw.horizontal_feed_tilt_season).toLowerCase() !== 'false',
    horizontalFeedTiltLastRun: String(raw.horizontal_feed_tilt_last_run).toLowerCase() !== 'false',
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

  if (top3IsShowing || overlayEventActive || isSplashViewActive()) {
    return;
  }

  const renderableViews = getRenderableViews(currentViews);
  const nextRenderKey = `${settings.showMedals}::${settings.horizontalLayout}::${settings.horizontalFeedSeason}::${settings.horizontalFeedToday}::${settings.horizontalFeedRacesSeason}::${settings.horizontalFeedBrsSeason}::${settings.horizontalFeedRacesToday}::${settings.horizontalFeedBrsToday}::${settings.horizontalFeedPreviousRace}::${settings.horizontalFeedEvents}::${settings.horizontalFeedTiltCurrent}::${settings.horizontalFeedTiltToday}::${settings.horizontalFeedTiltSeason}::${settings.horizontalFeedTiltLastRun}::${getViewsRenderKey(renderableViews)}`;

  if (nextRenderKey === lastRenderedViewsKey) {
    updateBoardTitleFromScroll();
    ensureLeaderboardAutoScroll();
    return;
  }

  lastRenderedViewsKey = nextRenderKey;
  renderCombinedRows(currentViews);
  ensureLeaderboardAutoScroll();
}

function normalizeOverlayMode(value) {
  const mode = String(value || '').trim().toLowerCase();
  if (mode === 'tilt' || mode === 'race' || mode === 'br' || mode === 'pre-game' || mode === 'post-race') return mode;
  return '';
}

function normalizeRaceType(value) {
  const type = String(value || '').trim().toLowerCase();
  if (type === 'br' || type === 'battle royale' || type === 'royale') return 'br';
  if (type === 'race') return 'race';
  return '';
}


function buildHorizontalTiltViews(tiltPayload = {}) {
  const views = [];
  const currentRun = tiltPayload?.current_run || {};
  const currentRows = Array.isArray(currentRun?.standings) ? currentRun.standings : [];
  if (currentRows.length) {
    views.push({
      id: 'tilt-current',
      title: `Tilt Current Run • L${Number(currentRun?.level || 0)}`,
      rows: currentRows.slice(0, 10).map((row, index) => ({
        placement: index + 1,
        name: row?.name || 'Unknown',
        points: Number(row?.points || 0),
      })),
    });
  }

  const todayRows = Array.isArray(tiltPayload?.today_standings) ? tiltPayload.today_standings : [];
  if (todayRows.length) {
    views.push({
      id: 'tilt-today',
      title: 'Tilt Top 10 Today',
      rows: todayRows.slice(0, 10).map((row, index) => ({
        placement: index + 1,
        name: row?.name || 'Unknown',
        points: Number(row?.points || 0),
      })),
    });
  }

  const seasonRows = Array.isArray(tiltPayload?.season_standings) ? tiltPayload.season_standings : [];
  if (seasonRows.length) {
    views.push({
      id: 'tilt-season',
      title: 'Tilt Top 10 Season',
      rows: seasonRows.slice(0, 10).map((row, index) => ({
        placement: index + 1,
        name: row?.name || 'Unknown',
        points: Number(row?.points || 0),
      })),
    });
  }

  const lastRun = tiltPayload?.last_run || {};
  const lastRunRows = Array.isArray(lastRun?.standings) ? lastRun.standings : [];
  if (lastRunRows.length) {
    views.push({
      id: 'tilt-last-run',
      title: `Tilt Last Run${lastRun?.run_id ? ` • ${String(lastRun.run_id).slice(0, 6)}` : ''}`,
      rows: lastRunRows.slice(0, 10).map((row, index) => ({
        placement: index + 1,
        name: row?.name || 'Unknown',
        points: Number(row?.points || 0),
      })),
    });
  }

  return views;
}

function selectViewsForMode(views = [], mode = '') {
  if (!mode) return Array.isArray(views) ? views : [];

  const byId = new Map((Array.isArray(views) ? views : []).map((view) => [String(view?.id || ''), view]));
  const orderedIds = mode === 'br'
    ? ['season', 'today', 'brs-season', 'brs-today', 'previous']
    : ['season', 'today', 'races-season', 'races-today', 'previous'];

  return orderedIds
    .map((id) => byId.get(id))
    .filter((view) => Array.isArray(view?.rows) && view.rows.length > 0);
}

async function refresh() {
  try {
    const r = await fetch('/api/overlay', { cache: 'no-store' });
    const payload = await r.json();
    const overlayMode = normalizeOverlayMode(payload?.active_mode);
    const racePayload = payload?.top3 || payload;
    const resolvedSceneMode = resolveSceneMode(racePayload, overlayMode);
    currentSceneMode = overlayMode === 'tilt' ? 'tilt' : resolvedSceneMode;

    if (currentSceneMode !== lastSceneMode) {
      const prettyScene = String(currentSceneMode || 'race').replace(/[-_]+/g, ' ');
      queueNarrativeEvent({
        type: 'scene mode',
        message: `Scene mode: ${prettyScene.toUpperCase()}`,
      });
      lastSceneMode = currentSceneMode;
    }

    currentLanguage = (racePayload?.settings?.language || 'en').toLowerCase();
    applyServerSettings(racePayload.settings || {});

    if (overlayMode === 'tilt' && !settings.horizontalLayout) {
      window.location.replace('/overlay');
      return;
    }

    if (overlayMode === 'tilt' && settings.horizontalLayout) {
      const tiltPayload = payload?.tilt || {};
      $('overlay-title').textContent = t(tiltPayload?.title || 'MyStats Tilt Run Tracker');
      updateHeaderStats({
        avg_points_today: tiltPayload?.current_run?.run_points || 0,
        unique_racers_today: Array.isArray(tiltPayload?.current_run?.standings) ? tiltPayload.current_run.standings.length : 0,
        total_races_today: tiltPayload?.current_run?.level || 0,
        avg_points_season: tiltPayload?.current_run?.best_run_xp_today || 0,
        unique_racers_season: Array.isArray(tiltPayload?.season_standings) ? tiltPayload.season_standings.length : 0,
        total_races_season: tiltPayload?.current_run?.total_xp_today || 0,
      });

      const overlayEvents = Array.isArray(racePayload?.overlay_events) ? racePayload.overlay_events : [];
      const tiltViews = buildHorizontalTiltViews(tiltPayload);
      const viewsToRender = filterViewsForHorizontalFeed(tiltViews, overlayEvents);
      syncViews(viewsToRender);
      return;
    }

    const p = racePayload;
    $('overlay-title').textContent = t(p.title || 'MyStats Live Results');
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

    const raceType = normalizeRaceType(p?.recent_race_top3?.race_type);
    if (overlayMode === 'race' || overlayMode === 'br') {
      currentResultsMode = overlayMode;
    } else if (raceType) {
      currentResultsMode = raceType;
    }

    const nextPillMode = currentResultsMode === 'br' ? 'br' : 'race';
    if (nextPillMode !== currentPillMode) {
      currentPillMode = nextPillMode;
      activePillPage = 0;
    }
    renderPillPage();

    const overlayEvents = Array.isArray(p.overlay_events) ? p.overlay_events : [];
    const filteredViews = selectViewsForMode(normalizedViews, currentResultsMode);
    const modeViews = filteredViews.length ? filteredViews : normalizedViews;
    const viewsToRender = settings.horizontalLayout
      ? filterViewsForHorizontalFeed(modeViews, overlayEvents)
      : modeViews;
    syncViews(viewsToRender);

    if (!hasHydratedOverlayEvents) {
      hasHydratedOverlayEvents = true;
      const maxHydratedEventId = overlayEvents.reduce((maxId, eventItem) => {
        const currentId = Number(eventItem?.id) || 0;
        return Math.max(maxId, currentId);
      }, 0);
      lastOverlayEventId = Math.max(lastOverlayEventId, maxHydratedEventId);
    } else {
      overlayEvents
        .filter((eventItem) => (Number(eventItem?.id) || 0) > lastOverlayEventId)
        .sort((a, b) => (Number(a?.id) || 0) - (Number(b?.id) || 0))
        .forEach((eventItem) => {
          lastOverlayEventId = Math.max(lastOverlayEventId, Number(eventItem?.id) || 0);
          queueOverlayEvent(eventItem);
        });
    }

    const raceKey = p.recent_race_top3?.race_key || null;
    if (!hasHydratedOnce) {
      hasHydratedOnce = true;
      lastRaceKey = raceKey;
      return;
    }

    if (raceKey && raceKey !== lastRaceKey) {
      lastRaceKey = raceKey;
      const firstPlace = Array.isArray(p?.recent_race_top3?.rows)
        ? p.recent_race_top3.rows.find((row) => Number(row?.placement) === 1)
        : null;
      if (firstPlace?.name) {
        const raceKind = normalizeRaceType(p?.recent_race_top3?.race_type);
        queueNarrativeEvent({
          type: raceKind === 'br' ? 'br winner' : 'race winner',
          message: `${firstPlace.name} won with ${fmt(firstPlace.points)} points`,
        });
      }
      queueTop3Overlay(p.recent_race_top3);
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


(function applyStaticTranslations(){
  const title = document.querySelector('.record-overlay__title');
  if (title) title.textContent = t('WORLD RECORD!');
  const mapping = {
    'stat-avg-today':'Avg Points Today','stat-uniq-today':'All Racers Today','stat-races-today':'Total Races Today',
    'stat-avg-season':'Avg Points Season','stat-uniq-season':'All Racers Season','stat-races-season':'Total Races Season',
    'stat-br-avg-today':'Avg Pts Per BR','stat-br-racers-today':'BR Racers Today','stat-br-total-today':'Total BRs Today'
  };
  Object.entries(mapping).forEach(([id,key]) => {
    const n = document.querySelector(`#${id} .pill-title`);
    if (n) n.textContent = t(key);
  });
})();
