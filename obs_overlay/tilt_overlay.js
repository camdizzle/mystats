const $ = (id) => document.getElementById(id);
const fmt = (n) => new Intl.NumberFormat().format(Number(n || 0));

let currentLanguage = 'en';
const I18N = {
  en: {},
  es: {
    'MyStats Tilt Run Tracker': 'MyStats Seguimiento de Tilt',
    'Active': 'Activo',
    'Idle': 'Inactivo',
    'No active run standings yet.': 'Aún no hay posiciones de la partida activa.',
    'No completed tilt run yet.': 'Aún no hay una partida tilt completada.',
    'No season standings yet.': 'Aún no hay posiciones de temporada.',
  },
  au: {
    'MyStats Tilt Run Tracker': 'MyStats Tilt Run Tracker, cobber',
    'Active': 'Flat Out',
    'Idle': 'Taking a Breather',
    'No active run standings yet.': 'No active run standings yet, still warming up.',
    'No completed tilt run yet.': 'No completed tilt run yet, hang tight.',
    'No season standings yet.': 'No season standings yet, still warming up.',
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
  ['updated', 'fresh off the barbie'],
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
  return slang;
}

const t = (key) => {
  const translated = I18N[currentLanguage]?.[key] || key;
  return currentLanguage === 'au' ? toAussieSlang(translated) : translated;
};

const defaultSettings = {
  refresh_seconds: 3,
  theme: 'midnight',
  card_opacity: 84,
  text_scale: 100,
  tilt_scroll_step_px: 1,
  tilt_scroll_interval_ms: 40,
  tilt_scroll_pause_ms: 900,
};

const themes = {
  midnight: { text: '#eef3ff', accent: '#7fd8ff', panelBase: '10,14,27', panel2Base: '22,33,57' },
  ocean: { text: '#ecf8ff', accent: '#78f1ff', panelBase: '4,24,35', panel2Base: '8,53,75' },
  sunset: { text: '#fff0fa', accent: '#ffc575', panelBase: '38,10,31', panel2Base: '81,20,63' },
  forest: { text: '#e9ffed', accent: '#7afec3', panelBase: '9,25,19', panel2Base: '17,64,47' },
  mono: { text: '#f4f6ff', accent: '#d2dcff', panelBase: '17,20,33', panel2Base: '40,46,72' },
  violethearts: { text: '#fff3ff', accent: '#9fd6ff', panelBase: '43,14,58', panel2Base: '121,41,148' },
};

let refreshTimer = null;
let refreshSeconds = 3;
const autoScrollTimers = new Map();
const autoScrollConfig = { stepPx: 1, intervalMs: 40, pauseMs: 900 };

let levelOverlayHideTimer = null;
let runOverlayHideTimer = null;
let lastLevelOverlayKey = '';
let lastRunOverlayKey = '';
let levelOverlayActive = false;
let runOverlayActive = false;
let overlayBaselineInitialized = false;
let lastRunCompletionEventId = 0;
let suppressRunCompletionUntilNewEvent = true;
let pendingRunCompletionEventId = 0;
let displayedRunCompletionEventId = 0;
const overlayStorageKey = 'mystats.tiltOverlay.snapshot.v1';

const activeSplashVariant = 'countdown';
document.body.dataset.splashVariant = activeSplashVariant;

const splashAnimationDurationMs = 9000;
const splashPostAnimationHoldMs = 1000;
const splashDurationMs = splashAnimationDurationMs + splashPostAnimationHoldMs;

const rotationConfig = {
  currentRunDurationMs: 15000,
  seasonTop10DurationMs: 15000,
};
let rotationReturnTimer = null;
let rotationView = 'standings';
let splashRestartTimer = null;

function setRotationView(view) {
  const allowed = new Set(['standings', 'summary', 'season']);
  rotationView = allowed.has(view) ? view : 'standings';
  document.body?.setAttribute('data-rotation-view', rotationView);
}

function clearRotationTimer() {
  if (rotationReturnTimer) {
    clearTimeout(rotationReturnTimer);
    rotationReturnTimer = null;
  }
}

function clearSplashRestartTimer() {
  if (splashRestartTimer) {
    clearTimeout(splashRestartTimer);
    splashRestartTimer = null;
  }
}

function isSplashViewActive() {
  return Boolean($('tilt-splash-screen')?.getAttribute('visible') === 'true');
}

function hideSplashView() {
  const splashScreen = $('tilt-splash-screen');
  if (!splashScreen) return;
  splashScreen.classList.remove('is-visible');
  splashScreen.classList.remove('splash-animate');
  splashScreen.setAttribute('aria-hidden', 'true');
  splashScreen.setAttribute('visible', 'false');
}

function showSplashView() {
  const splashScreen = $('tilt-splash-screen');
  if (!splashScreen) {
    setRotationView('standings');
    startAutoScroll('current-standings');
    return;
  }

  stopAutoScroll('current-standings');
  stopAutoScroll('season-standings');
  setRotationView('standings');

  splashScreen.classList.add('is-visible');
  splashScreen.classList.remove('splash-animate');
  void splashScreen.offsetWidth;
  splashScreen.classList.add('splash-animate');
  splashScreen.setAttribute('aria-hidden', 'false');
  splashScreen.setAttribute('visible', 'true');

  clearSplashRestartTimer();
  splashRestartTimer = setTimeout(() => {
    hideSplashView();
    setRotationView('standings');
    startAutoScroll('current-standings');
  }, splashDurationMs);
}

function showSeasonTop10Temporarily() {
  if (rotationView === 'season') return;
  clearRotationTimer();
  clearSplashRestartTimer();
  stopAutoScroll('current-standings');
  setRotationView('season');
  startAutoScroll('season-standings');

  rotationReturnTimer = setTimeout(() => {
    stopAutoScroll('season-standings');
    showSplashView();
    rotationReturnTimer = null;
  }, rotationConfig.seasonTop10DurationMs);
}

function showCurrentRunSummaryTemporarily() {
  if (rotationView === 'summary') return;
  clearRotationTimer();
  clearSplashRestartTimer();
  stopAutoScroll('current-standings');
  setRotationView('summary');

  rotationReturnTimer = setTimeout(() => {
    showSeasonTop10Temporarily();
    rotationReturnTimer = null;
  }, rotationConfig.currentRunDurationMs);
}


function saveOverlaySnapshot(payload = {}) {
  try {
    const snapshot = {
      savedAt: Date.now(),
      title: payload.title || 'MyStats Tilt Run Tracker',
      current_run: payload.current_run || {},
      last_run: payload.last_run || {},
      level_completion: payload.level_completion || {},
      run_completion: payload.run_completion || {},
      run_completion_event_id: Math.max(0, Number(payload.run_completion_event_id || 0)),
      settings: payload.settings || {},
      season_standings: Array.isArray(payload.season_standings) ? payload.season_standings : [],
    };
    window.localStorage?.setItem(overlayStorageKey, JSON.stringify(snapshot));
  } catch (error) {
    // Best-effort cache. Ignore storage failures (private mode / quota).
  }
}

function loadOverlaySnapshot() {
  try {
    const raw = window.localStorage?.getItem(overlayStorageKey);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return null;

    const savedAt = Number(parsed.savedAt || 0);
    const maxSnapshotAgeMs = 6 * 60 * 60 * 1000;
    if (!savedAt || Date.now() - savedAt > maxSnapshotAgeMs) return null;

    return parsed;
  } catch (error) {
    return null;
  }
}

function renderSnapshot(snapshot = {}) {
  currentLanguage = String(snapshot?.settings?.language || currentLanguage || 'en').toLowerCase();
  $('overlay-title').textContent = t(snapshot.title || 'MyStats Tilt Run Tracker');
  applyTheme(snapshot.settings || {});
  renderCurrentRun(snapshot.current_run || {});
  renderSeasonStandings(snapshot.season_standings || []);
  renderLastRun(snapshot.last_run || {});
}

function setLevelOverlayVisible(isVisible) {
  const levelOverlay = $('level-complete-overlay');
  if (!levelOverlay) return;
  levelOverlay.hidden = !isVisible;
  levelOverlay.style.display = isVisible ? '' : 'none';
  levelOverlay.setAttribute('aria-hidden', isVisible ? 'false' : 'true');
}

function setRunOverlayVisible(isVisible) {
  const runOverlay = $('run-complete-overlay');
  if (!runOverlay) return;
  runOverlay.hidden = !isVisible;
  runOverlay.style.display = isVisible ? '' : 'none';
  runOverlay.setAttribute('aria-hidden', isVisible ? 'false' : 'true');
}

function getLevelOverlayKey(level = {}) {
  const levelNum = Number(level.level || 0);
  const completedAt = String(level.completed_at || '').trim();
  if (!levelNum || !completedAt) return '';
  return `${levelNum}|${completedAt}`;
}

function getRunOverlayKey(runCompletion = {}) {
  const hasRun = !!(runCompletion && runCompletion.run_id && runCompletion.ended_at);
  if (!hasRun) return '';
  return `${runCompletion.run_id}|${runCompletion.ended_at}`;
}

function hideRecapOverlays() {
  if (levelOverlayHideTimer) clearTimeout(levelOverlayHideTimer);
  if (runOverlayHideTimer) clearTimeout(runOverlayHideTimer);
  levelOverlayHideTimer = null;
  runOverlayHideTimer = null;
  clearRotationTimer();
  clearSplashRestartTimer();
  levelOverlayActive = false;
  runOverlayActive = false;
  setLevelOverlayVisible(false);
  setRunOverlayVisible(false);
  hideSplashView();
  updateTrackerVisibility();
}

function hideLevelCompletionOverlay() {
  if (levelOverlayHideTimer) clearTimeout(levelOverlayHideTimer);
  levelOverlayHideTimer = null;
  levelOverlayActive = false;
  setLevelOverlayVisible(false);
  updateTrackerVisibility();
}

function hideRunCompletionOverlay() {
  if (runOverlayHideTimer) clearTimeout(runOverlayHideTimer);
  runOverlayHideTimer = null;
  runOverlayActive = false;
  setRunOverlayVisible(false);
  updateTrackerVisibility();
}

function stopAutoScroll(listId) {
  const timerId = autoScrollTimers.get(listId);
  if (timerId) {
    clearInterval(timerId);
    autoScrollTimers.delete(listId);
  }
}

function syncStandingsEndSpacer(listId) {
  const host = $(listId);
  if (!host) return;
  const endSpacer = host.querySelector('.standings-end-spacer');
  if (!endSpacer) return;
  endSpacer.style.height = `${host.clientHeight}px`;
}

function updateTrackerVisibility() {
  const tracker = $('tilt-tracker-card');
  const levelOverlay = $('level-complete-overlay');
  const runOverlay = $('run-complete-overlay');

  // Keep state resilient if markup starts hidden or another code path hides an overlay.
  if (!levelOverlay || levelOverlay.hidden) levelOverlayActive = false;
  if (!runOverlay || runOverlay.hidden) runOverlayActive = false;

  // Defensive reconciliation: if overlay state says inactive, force-hide any lingering overlay DOM.
  if (levelOverlay && !levelOverlayActive && !levelOverlay.hidden) {
    setLevelOverlayVisible(false);
  }
  if (runOverlay && !runOverlayActive && !runOverlay.hidden) {
    setRunOverlayVisible(false);
  }

  const showingRecap =
    (levelOverlayActive && !!levelOverlay && !levelOverlay.hidden)
    || (runOverlayActive && !!runOverlay && !runOverlay.hidden);

  if (tracker) tracker.hidden = showingRecap;
  document.body?.setAttribute('data-overlay-mode', showingRecap ? 'recap' : 'tracker');
}

function startAutoScroll(listId) {
  const host = $(listId);
  if (!host) return;
  if (listId === 'current-standings' && rotationView !== 'standings') return;
  if (listId === 'season-standings' && rotationView !== 'season') return;

  stopAutoScroll(listId);
  host.scrollTop = 0;
  host.dataset.scrollLock = 'false';

  const endSpacer = host.querySelector('.standings-end-spacer');
  const initialTransitionTop = endSpacer ? endSpacer.offsetTop : 0;
  const initialMaxScrollTop = Math.max(0, host.scrollHeight - host.clientHeight);
  if (initialMaxScrollTop <= 0 && initialTransitionTop <= 0) return;

  const timerId = setInterval(() => {
    // Recompute bounds on every tick so we recover after overlays/splash hide or layout changes.
    const maxScrollTop = Math.max(0, host.scrollHeight - host.clientHeight);
    const transitionSpacer = host.querySelector('.standings-end-spacer');
    // Keep trigger within reachable scroll bounds. offsetTop can exceed maxScrollTop.
    const transitionTop = Math.min(maxScrollTop, transitionSpacer ? transitionSpacer.offsetTop : maxScrollTop);

    // Ignore ticks while the list is not measurable (e.g. tracker hidden under recap overlays).
    if (host.clientHeight <= 0) return;
    if (maxScrollTop <= 0) return;
    if (host.dataset.scrollLock === 'true') return;

    host.scrollTop = Math.min(maxScrollTop, host.scrollTop + autoScrollConfig.stepPx);

    if (host.scrollTop >= transitionTop - 1) {
      host.dataset.scrollLock = 'true';
      setTimeout(() => {
        if (!autoScrollTimers.has(listId)) return;
        host.scrollTop = 0;
        host.dataset.scrollLock = 'false';
        if (listId === 'current-standings') {
          showCurrentRunSummaryTemporarily();
        }
      }, autoScrollConfig.pauseMs);
    }
  }, autoScrollConfig.intervalMs);

  autoScrollTimers.set(listId, timerId);
}

function applyTheme(settings = {}) {
  const merged = { ...defaultSettings, ...(settings || {}) };
  const theme = themes[(merged.theme || 'midnight').toLowerCase()] || themes.midnight;
  const opacity = Math.max(65, Math.min(100, Number(merged.card_opacity || 84))) / 100;
  const textScale = Math.max(75, Math.min(175, Number(merged.text_scale || 100))) / 100;

  const root = document.documentElement;
  root.style.setProperty('--text', theme.text);
  root.style.setProperty('--accent', theme.accent);
  root.style.setProperty('--panel', `rgba(${theme.panelBase}, ${opacity})`);
  root.style.setProperty('--panel-2', `rgba(${theme.panel2Base}, ${Math.max(0.6, opacity - 0.08)})`);
  root.style.setProperty('--text-scale', textScale.toString());

  autoScrollConfig.stepPx = Math.max(1, Math.min(4, Number(merged.tilt_scroll_step_px || defaultSettings.tilt_scroll_step_px)));
  autoScrollConfig.intervalMs = Math.max(20, Math.min(120, Number(merged.tilt_scroll_interval_ms || defaultSettings.tilt_scroll_interval_ms)));
  autoScrollConfig.pauseMs = Math.max(0, Math.min(3000, Number(merged.tilt_scroll_pause_ms || defaultSettings.tilt_scroll_pause_ms)));
}

function renderStandings(listId, standings, emptyText, limit = null) {
  const host = $(listId);
  if (!host) return;

  const normalizedRows = Array.isArray(standings) ? (Number.isFinite(limit) ? standings.slice(0, Math.max(0, limit)) : standings) : [];
  const hasRows = normalizedRows.length > 0;
  const rowsMarkup = hasRows
    ? normalizedRows
      .map((row, i) => {
        const deaths = Number(row.deaths ?? row.death_count ?? row.total_deaths ?? row.run_deaths ?? 0);
        return `<li><span>#${i + 1} ${row.name}</span><span>${fmt(row.points)} pts · ☠ ${fmt(deaths)}</span></li>`;
      })
      .join('')
    : '';
  const renderKey = hasRows ? rowsMarkup : `__empty__:${emptyText}`;

  if (host.dataset.renderKey === renderKey) {
    if (listId === 'current-standings' && hasRows && !autoScrollTimers.has(listId)) {
      startAutoScroll(listId);
    }
    return;
  }

  host.dataset.renderKey = renderKey;
  host.dataset.loopHeight = '0';

  if (!hasRows) {
    host.innerHTML = `<li>${emptyText}</li>`;
    if (listId === 'current-standings') {
      clearRotationTimer();
      clearSplashRestartTimer();
      hideSplashView();
      setRotationView('standings');
      stopAutoScroll('current-standings');
      stopAutoScroll('season-standings');
    }
    return;
  }

  host.innerHTML = `${rowsMarkup}<li class="standings-end-spacer" aria-hidden="true"></li>`;
  syncStandingsEndSpacer(listId);

  if (listId === 'current-standings') {
    if (rotationView === 'standings' && !isSplashViewActive()) startAutoScroll(listId);
  }

  if (listId === 'season-standings' && rotationView === 'season') {
    startAutoScroll(listId);
  }
}

function renderCurrentRun(run = {}) {
  const isActive = run.status === 'active';
  $('run-status-value').textContent = isActive ? t('Active') : t('Idle');
  $('run-status').classList.toggle('pill--active', isActive);
  $('run-level-value').textContent = fmt(run.level);
  $('run-elapsed-value').textContent = run.elapsed_time || '0:00';

  const leader = run.leader ? `${run.leader.name} (${fmt(run.leader.points)} pts)` : 'None';
  const topTiltee = run.top_tiltee || 'None';
  const topTilteeCount = Number(run.top_tiltee_count || 0);
  const topTilteeWithCount = topTiltee === 'None' ? 'None' : `${topTiltee} (${fmt(topTilteeCount)} tops)`;
  $('current-leader').textContent = leader;
  $('current-top-tiltee').textContent = topTilteeWithCount;
  $('top-tiltee-value').textContent = topTiltee;
  $('current-run-points').textContent = fmt(run.run_points);
  $('current-run-xp').textContent = fmt(run.run_xp);
  $('best-run-xp').textContent = fmt(run.best_run_xp_today);
  $('total-xp-today').textContent = fmt(run.total_xp_today);
  $('total-deaths-today').textContent = fmt(run.total_deaths_today);
  $('lifetime-xp').textContent = fmt(run.lifetime_expertise);

  renderStandings('current-standings', run.standings, t('No active run standings yet.'));
}

function renderSeasonStandings(seasonStandings = []) {
  renderStandings('season-standings', seasonStandings, t('No season standings yet.'), 10);
}

function isLastRunFromToday(lastRun = {}) {
  const endedAt = String(lastRun?.ended_at || '').trim();
  if (!endedAt) return false;

  const dateMatch = endedAt.match(/^(\d{4}-\d{2}-\d{2})/);
  if (!dateMatch) return true;

  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, '0');
  const dd = String(today.getDate()).padStart(2, '0');
  const todayKey = `${yyyy}-${mm}-${dd}`;
  return dateMatch[1] === todayKey;
}

function renderLastRun(lastRun = {}) {
  const summary = $('last-run-summary');
  const section = $('last-run-section');
  const hasRunId = !!(lastRun && lastRun.run_id);
  const hasRecentRun = hasRunId && isLastRunFromToday(lastRun);

  document.body?.setAttribute('data-has-last-run', hasRecentRun ? 'true' : 'false');

  if (section) {
    section.hidden = !hasRecentRun;
    section.style.display = hasRecentRun ? '' : 'none';
  }

  if (!hasRecentRun) {
    summary.textContent = t('No completed tilt run yet.');
    return;
  }

  const leaderText = lastRun.leader ? `${lastRun.leader.name} (${fmt(lastRun.leader.points)} pts)` : 'None';
  summary.innerHTML = [
    `<span class="summary__item"><span class="summary__label">Level</span>${fmt(lastRun.ended_level)}</span>`,
    `<span class="summary__item"><span class="summary__label">Total Time</span>${lastRun.total_time || lastRun.elapsed_time || '0:00'}</span>`,
    `<span class="summary__item"><span class="summary__label">Leader</span>${leaderText}</span>`,
    `<span class="summary__item"><span class="summary__label">Run Pts</span>${fmt(lastRun.run_points)}</span>`,
    `<span class="summary__item"><span class="summary__label">Run Expertise</span>${fmt(lastRun.run_expertise ?? lastRun.run_xp)}</span>`,
    `<span class="summary__item"><span class="summary__label">Ended</span>${lastRun.ended_at || 'n/a'}</span>`,
  ].join('');
}

function renderLevelCompletionOverlay(level = {}) {
  const host = $('level-complete-overlay');
  const stats = $('level-complete-stats');
  const title = $('level-complete-title');
  const subtitle = $('level-complete-subtitle');
  if (!host || !stats) return false;

  const overlayKey = getLevelOverlayKey(level);
  if (!overlayKey) {
    if (!levelOverlayActive) {
      setLevelOverlayVisible(false);
      updateTrackerVisibility();
    }
    return false;
  }

  if (overlayKey === lastLevelOverlayKey) return false;
  lastLevelOverlayKey = overlayKey;

  const levelNum = Number(level.level || 0);

  const deathRate = Number(level.death_rate || 0).toFixed(1);
  const survivalRate = Number(level.survival_rate || 0).toFixed(1);

  if (title) title.textContent = `Level ${fmt(levelNum)} Complete`;
  if (subtitle) subtitle.textContent = `${level.top_tiltee || 'None'} owned this round`;

  const topTiltee = level.top_tiltee || 'None';
  stats.innerHTML = `
    <div class="overlay-hero">
      <div class="overlay-hero__label">Top Tiltee</div>
      <div class="overlay-hero__value">${topTiltee}</div>
    </div>
    <div class="overlay-pill-row">
      <div class="overlay-pill">⏱ ${level.elapsed_time || '0:00'}</div>
      <div class="overlay-pill">⭐ ${fmt(level.level_points)} pts</div>
      <div class="overlay-pill">✨ +${fmt(level.earned_xp)} XP</div>
    </div>
    <div class="overlay-metrics">
      <div class="overlay-metric"><span>Survivors</span><strong>${fmt(level.survivors)}</strong></div>
      <div class="overlay-metric"><span>Deaths</span><strong>${fmt(level.deaths)}</strong></div>
      <div class="overlay-metric"><span>Death Rate</span><strong>${deathRate}%</strong></div>
      <div class="overlay-metric"><span>Survival</span><strong>${survivalRate}%</strong></div>
    </div>
  `;

  levelOverlayActive = true;
  hideRunCompletionOverlay();
  updateTrackerVisibility();
  setLevelOverlayVisible(true);

  if (levelOverlayHideTimer) clearTimeout(levelOverlayHideTimer);
  levelOverlayHideTimer = setTimeout(() => {
    setLevelOverlayVisible(false);
    levelOverlayActive = false;
    updateTrackerVisibility();
  }, 10000);

  return true;
}

function renderRunCompletionOverlay(lastRun = {}, shouldDisplay = true) {
  const host = $('run-complete-overlay');
  const title = $('run-complete-title');
  const subtitle = $('run-complete-subtitle');
  const top3 = $('run-complete-top3');
  const stats = $('run-complete-stats');
  if (!host || !title || !subtitle || !top3 || !stats) return false;

  const runKey = getRunOverlayKey(lastRun);
  if (!shouldDisplay || !runKey) return false;
  if (runKey === lastRunOverlayKey) return false;
  lastRunOverlayKey = runKey;

  const standings = Array.isArray(lastRun.standings) ? lastRun.standings.slice(0, 3) : [];
  const runDeaths = Number(
    lastRun.deaths
    ?? lastRun.run_deaths
    ?? lastRun.total_deaths
    ?? lastRun.total_deaths_today
    ?? 0
  );
  const runDeathRateRaw = Number(
    lastRun.death_rate
    ?? lastRun.run_death_rate
    ?? 0
  );
  const runDeathRate = runDeathRateRaw.toFixed(1);

  title.textContent = `Run Complete • Level ${fmt(lastRun.ended_level)}`;
  subtitle.textContent = `${lastRun.total_time || lastRun.elapsed_time || '0:00'} total • ${fmt(lastRun.run_expertise ?? lastRun.run_xp)} XP gained`;

  top3.innerHTML = standings.length
    ? standings.map((row, i) => `
      <li>
        <span class="run-overlay__rank run-overlay__rank--${i + 1}">${i + 1}</span>
        <span class="run-overlay__name">${row.name}</span>
        <span class="run-overlay__points">${fmt(row.points)} pts</span>
      </li>
    `).join('')
    : '<li><span class="run-overlay__rank run-overlay__rank--1">1</span><span class="run-overlay__name">No results</span><span class="run-overlay__points">-</span></li>';

  stats.innerHTML = `
    <div class="overlay-hero overlay-hero--run">
      <div class="overlay-hero__label">Top Tiltee</div>
      <div class="overlay-hero__value">${lastRun.top_tiltee || 'None'}</div>
    </div>
    <div class="overlay-pill-row overlay-pill-row--run">
      <div class="overlay-pill">🏆 ${fmt(lastRun.run_points)} pts</div>
      <div class="overlay-pill">✨ ${fmt(lastRun.run_expertise ?? lastRun.run_xp)} XP</div>
      <div class="overlay-pill">💀 ${fmt(runDeaths)} deaths</div>
      <div class="overlay-pill">📉 ${runDeathRate}% death rate</div>
      <div class="overlay-pill">🔥 Best ${fmt(lastRun.best_run_xp_today)} XP</div>
    </div>
  `;

  runOverlayActive = true;
  levelOverlayActive = false;
  setLevelOverlayVisible(false);
  updateTrackerVisibility();
  setRunOverlayVisible(true);

  if (runOverlayHideTimer) clearTimeout(runOverlayHideTimer);
  runOverlayHideTimer = setTimeout(() => {
    setRunOverlayVisible(false);
    runOverlayActive = false;
    updateTrackerVisibility();
  }, 15000);

  return true;
}

async function refresh() {
  try {
    const response = await fetch('/api/overlay/tilt', { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const payload = await response.json();
    saveOverlaySnapshot(payload);
    currentLanguage = String(payload?.settings?.language || currentLanguage || 'en').toLowerCase();
    $('overlay-title').textContent = t(payload.title || 'MyStats Tilt Run Tracker');

    const currentRun = payload.current_run || {};
    const currentStatus = currentRun.status === 'active' ? 'active' : 'idle';

    const runCompletion = payload.run_completion || {};
    const runCompletionEventId = Math.max(0, Number(payload.run_completion_event_id || 0));

    if (!overlayBaselineInitialized) {
      lastLevelOverlayKey = getLevelOverlayKey(payload.level_completion || {});
      lastRunOverlayKey = getRunOverlayKey(runCompletion);
      lastRunCompletionEventId = runCompletionEventId;
      pendingRunCompletionEventId = 0;
      displayedRunCompletionEventId = runCompletionEventId;
      suppressRunCompletionUntilNewEvent = true;
      hideRecapOverlays();
      overlayBaselineInitialized = true;
    }

    if (currentStatus === 'active') {
      hideRunCompletionOverlay();
    }

    applyTheme(payload.settings || {});

    const refreshFromPayload = Number(payload.settings?.refresh_seconds || defaultSettings.refresh_seconds);
    const newRefresh = Math.max(1, Math.min(30, refreshFromPayload));
    if (newRefresh !== refreshSeconds) {
      refreshSeconds = newRefresh;
      startRefreshTimer();
    }

    renderCurrentRun(currentRun);
    renderSeasonStandings(payload.season_standings || []);
    renderLastRun(payload.last_run || {});
    const levelRecapShown = renderLevelCompletionOverlay(payload.level_completion || {});
    if (levelRecapShown || runOverlayActive) {
      hideSplashView();
      clearSplashRestartTimer();
      stopAutoScroll('current-standings');
      stopAutoScroll('season-standings');
    }

    const hasNewRunCompletionEvent = runCompletionEventId > lastRunCompletionEventId;
    if (hasNewRunCompletionEvent) {
      pendingRunCompletionEventId = runCompletionEventId;
      lastRunCompletionEventId = runCompletionEventId;
      suppressRunCompletionUntilNewEvent = false;
    }

    const hasPendingRunCompletionEvent = pendingRunCompletionEventId > displayedRunCompletionEventId;
    if (currentStatus === 'idle' && !suppressRunCompletionUntilNewEvent && hasPendingRunCompletionEvent && !levelRecapShown) {
      const runRecapShown = renderRunCompletionOverlay(runCompletion);
      if (runRecapShown) {
        displayedRunCompletionEventId = pendingRunCompletionEventId;
        pendingRunCompletionEventId = 0;
      }
    } else if (hasPendingRunCompletionEvent && levelRecapShown) {
      // Preserve the event while level recap is visible and show run recap on the next refresh.
      // Intentionally keep pendingRunCompletionEventId set until level recap clears.
    }

  } catch (e) {
    $('run-status-value').textContent = 'Unavailable';
    $('last-run-summary').textContent = 'Unable to load tilt overlay data from /api/overlay/tilt.';
    hideRecapOverlays();
    // Keep baseline/event memory across transient fetch errors so historical run-complete events are not retriggered.
    updateTrackerVisibility();
  }
}

function startRefreshTimer() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(refresh, refreshSeconds * 1000);
}

window.addEventListener('resize', () => {
  syncStandingsEndSpacer('current-standings');
  syncStandingsEndSpacer('season-standings');
});

setRotationView('standings');

const initialSnapshot = loadOverlaySnapshot();
if (initialSnapshot) {
  renderSnapshot(initialSnapshot);
}

refresh();
startRefreshTimer();

// Ensure recap overlays are hidden before the first payload is processed.
hideRecapOverlays();
hideLevelCompletionOverlay();
hideRunCompletionOverlay();
const tracker = $('tilt-tracker-card');
if (tracker) tracker.hidden = false;
document.body?.setAttribute('data-overlay-mode', 'tracker');
