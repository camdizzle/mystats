const $ = (id) => document.getElementById(id);
const fmt = (n) => new Intl.NumberFormat().format(Number(n || 0));

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
  const levelOverlay = $('level-complete-overlay');
  const runOverlay = $('run-complete-overlay');
  if (levelOverlayHideTimer) clearTimeout(levelOverlayHideTimer);
  if (runOverlayHideTimer) clearTimeout(runOverlayHideTimer);
  levelOverlayHideTimer = null;
  runOverlayHideTimer = null;
  levelOverlayActive = false;
  runOverlayActive = false;
  if (levelOverlay) levelOverlay.hidden = true;
  if (runOverlay) runOverlay.hidden = true;
  updateTrackerVisibility();
}

function hideRunCompletionOverlay() {
  const runOverlay = $('run-complete-overlay');
  if (runOverlayHideTimer) clearTimeout(runOverlayHideTimer);
  runOverlayHideTimer = null;
  runOverlayActive = false;
  if (runOverlay) runOverlay.hidden = true;
  updateTrackerVisibility();
}

function stopAutoScroll(listId) {
  const timerId = autoScrollTimers.get(listId);
  if (timerId) {
    clearInterval(timerId);
    autoScrollTimers.delete(listId);
  }
}

function updateTrackerVisibility() {
  const tracker = $('tilt-tracker-card');
  const levelOverlay = $('level-complete-overlay');
  const runOverlay = $('run-complete-overlay');

  // Keep state resilient if markup starts hidden or another code path hides an overlay.
  if (!levelOverlay || levelOverlay.hidden) levelOverlayActive = false;
  if (!runOverlay || runOverlay.hidden) runOverlayActive = false;

  const showingRecap =
    (levelOverlayActive && !!levelOverlay && !levelOverlay.hidden)
    || (runOverlayActive && !!runOverlay && !runOverlay.hidden);

  if (tracker) tracker.hidden = showingRecap;
  document.body?.setAttribute('data-overlay-mode', showingRecap ? 'recap' : 'tracker');
}

function startAutoScroll(listId) {
  const host = $(listId);
  if (!host) return;

  stopAutoScroll(listId);
  host.scrollTop = 0;

  const maxScrollTop = host.scrollHeight - host.clientHeight;
  if (maxScrollTop <= 0) return;

  let direction = 1;
  let isPaused = false;
  const timerId = setInterval(() => {
    if (isPaused) return;

    host.scrollTop = host.scrollTop + direction * autoScrollConfig.stepPx;

    if (host.scrollTop >= maxScrollTop) {
      host.scrollTop = maxScrollTop;
      direction = -1;
      isPaused = true;
      setTimeout(() => { isPaused = false; }, autoScrollConfig.pauseMs);
    } else if (host.scrollTop <= 0) {
      host.scrollTop = 0;
      direction = 1;
      isPaused = true;
      setTimeout(() => { isPaused = false; }, autoScrollConfig.pauseMs);
    }
  }, autoScrollConfig.intervalMs);

  autoScrollTimers.set(listId, timerId);
}

function applyTheme(settings = {}) {
  const merged = { ...defaultSettings, ...(settings || {}) };
  const theme = themes[(merged.theme || 'midnight').toLowerCase()] || themes.midnight;
  const opacity = Math.max(65, Math.min(100, Number(merged.card_opacity || 84))) / 100;
  const textScale = Math.max(90, Math.min(125, Number(merged.text_scale || 100))) / 100;

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

function renderStandings(listId, standings, emptyText) {
  const host = $(listId);
  if (!host) return;
  if (!Array.isArray(standings) || standings.length === 0) {
    host.innerHTML = `<li>${emptyText}</li>`;
    if (listId === 'current-standings') stopAutoScroll(listId);
    return;
  }

  host.innerHTML = standings
    .map((row, i) => `<li><span>#${i + 1} ${row.name}</span><span>${fmt(row.points)} pts</span></li>`)
    .join('');

  if (listId === 'current-standings') startAutoScroll(listId);
}

function renderCurrentRun(run = {}) {
  const isActive = run.status === 'active';
  $('run-status').textContent = `Status: ${isActive ? 'Active' : 'Idle'}`;
  $('run-status').classList.toggle('pill--active', isActive);
  $('run-level').textContent = `Level: ${fmt(run.level)}`;
  $('run-elapsed').textContent = `Elapsed: ${run.elapsed_time || '0:00'}`;

  const leader = run.leader ? `${run.leader.name} (${fmt(run.leader.points)} pts)` : 'None';
  const topTiltee = run.top_tiltee || 'None';
  $('current-leader').textContent = leader;
  $('current-top-tiltee').textContent = topTiltee;
  $('top-tiltee-pill').textContent = `Top Tiltee: ${topTiltee}`;
  $('current-run-points').textContent = fmt(run.run_points);
  $('current-run-xp').textContent = fmt(run.run_xp);
  $('best-run-xp').textContent = fmt(run.best_run_xp_today);
  $('total-xp-today').textContent = fmt(run.total_xp_today);
  $('total-deaths-today').textContent = fmt(run.total_deaths_today);
  $('lifetime-xp').textContent = fmt(run.lifetime_expertise);

  renderStandings('current-standings', run.standings, 'No active run standings yet.');
}

function renderLastRun(lastRun = {}) {
  const summary = $('last-run-summary');
  const hasRun = !!(lastRun && lastRun.run_id);
  if (!hasRun) {
    summary.textContent = 'No completed tilt run yet.';
    return;
  }

  const leaderText = lastRun.leader ? `${lastRun.leader.name} (${fmt(lastRun.leader.points)} pts)` : 'None';
  summary.innerHTML = [
    `<span class="summary__item"><span class="summary__label">Level</span>${fmt(lastRun.ended_level)}</span>`,
    `<span class="summary__item"><span class="summary__label">Time</span>${lastRun.elapsed_time || '0:00'}</span>`,
    `<span class="summary__item"><span class="summary__label">Leader</span>${leaderText}</span>`,
    `<span class="summary__item"><span class="summary__label">Run Pts</span>${fmt(lastRun.run_points)}</span>`,
    `<span class="summary__item"><span class="summary__label">Run XP</span>${fmt(lastRun.run_xp)}</span>`,
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
      host.hidden = true;
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
  host.hidden = false;

  if (levelOverlayHideTimer) clearTimeout(levelOverlayHideTimer);
  levelOverlayHideTimer = setTimeout(() => {
    host.hidden = true;
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
  title.textContent = `Run Complete • Level ${fmt(lastRun.ended_level)}`;
  subtitle.textContent = `${lastRun.elapsed_time || '0:00'} total • ${fmt(lastRun.run_xp)} XP gained`;

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
    <div class="overlay-pill-row">
      <div class="overlay-pill">🏆 ${fmt(lastRun.run_points)} pts</div>
      <div class="overlay-pill">✨ ${fmt(lastRun.run_xp)} XP</div>
      <div class="overlay-pill">💀 ${fmt(lastRun.total_deaths_today)} deaths</div>
      <div class="overlay-pill">🔥 Best ${fmt(lastRun.best_run_xp_today)} XP</div>
    </div>
  `;

  runOverlayActive = true;
  levelOverlayActive = false;
  const levelOverlay = $('level-complete-overlay');
  if (levelOverlay) levelOverlay.hidden = true;
  updateTrackerVisibility();
  host.hidden = false;

  if (runOverlayHideTimer) clearTimeout(runOverlayHideTimer);
  runOverlayHideTimer = setTimeout(() => {
    host.hidden = true;
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
    $('overlay-title').textContent = payload.title || 'MyStats Tilt Run Tracker';

    const currentRun = payload.current_run || {};
    const currentStatus = currentRun.status === 'active' ? 'active' : 'idle';

    const runCompletion = payload.run_completion || {};
    const runCompletionEventId = Math.max(0, Number(payload.run_completion_event_id || 0));

    if (!overlayBaselineInitialized) {
      lastLevelOverlayKey = getLevelOverlayKey(payload.level_completion || {});
      lastRunOverlayKey = getRunOverlayKey(runCompletion);
      lastRunCompletionEventId = runCompletionEventId;
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
    renderLastRun(payload.last_run || {});
    const levelRecapShown = renderLevelCompletionOverlay(payload.level_completion || {});

    const hasNewRunCompletionEvent = runCompletionEventId > lastRunCompletionEventId;
    if (hasNewRunCompletionEvent) {
      suppressRunCompletionUntilNewEvent = false;
    }

    if (currentStatus === 'idle' && !suppressRunCompletionUntilNewEvent && hasNewRunCompletionEvent && !levelRecapShown) {
      const runRecapShown = renderRunCompletionOverlay(runCompletion);
      if (runRecapShown) {
        lastRunCompletionEventId = runCompletionEventId;
      }
    } else if (hasNewRunCompletionEvent && levelRecapShown) {
      // Preserve the event while level recap is visible and show run recap on the next refresh.
      // Intentionally do not advance lastRunCompletionEventId here.
    } else if (!hasNewRunCompletionEvent && runCompletionEventId > 0) {
      lastRunCompletionEventId = runCompletionEventId;
    }

  } catch (e) {
    $('run-status').textContent = 'Status: Unavailable';
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

refresh();
startRefreshTimer();

// Ensure recap overlays are hidden before the first payload is processed.
hideRecapOverlays();
