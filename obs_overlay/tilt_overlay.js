const $ = (id) => document.getElementById(id);
const fmt = (n) => new Intl.NumberFormat().format(Number(n || 0));

const defaultSettings = {
  refresh_seconds: 3,
  theme: 'midnight',
  card_opacity: 84,
  text_scale: 100,
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
}

function renderStandings(listId, standings, emptyText) {
  const host = $(listId);
  if (!host) return;
  if (!Array.isArray(standings) || standings.length === 0) {
    host.innerHTML = `<li>${emptyText}</li>`;
    return;
  }

  host.innerHTML = standings
    .slice(0, 10)
    .map((row, i) => `<li><span>#${i + 1} ${row.name}</span><span>${fmt(row.points)} pts</span></li>`)
    .join('');
}

function renderCurrentRun(run = {}) {
  const isActive = run.status === 'active';
  $('run-status').textContent = `Status: ${isActive ? 'Active' : 'Idle'}`;
  $('run-status').classList.toggle('pill--active', isActive);
  $('run-id').textContent = `Run: ${run.run_short_id || '-'}`;
  $('run-level').textContent = `Level: ${fmt(run.level)}`;
  $('run-elapsed').textContent = `Elapsed: ${run.elapsed_time || '0:00'}`;

  const leader = run.leader ? `${run.leader.name} (${fmt(run.leader.points)} pts)` : 'None';
  $('current-leader').textContent = leader;
  $('current-top-tiltee').textContent = run.top_tiltee || 'None';
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
    renderStandings('last-run-standings', [], 'Waiting for first completed run.');
    return;
  }

  const leaderText = lastRun.leader ? `${lastRun.leader.name} (${fmt(lastRun.leader.points)} pts)` : 'None';
  summary.textContent = `Run ${lastRun.run_short_id || '-'} ended at level ${fmt(lastRun.ended_level)} (${lastRun.elapsed_time || '0:00'}). Leader: ${leaderText}. Run points: ${fmt(lastRun.run_points)} | Run XP: ${fmt(lastRun.run_xp)} | Ended: ${lastRun.ended_at || 'n/a'}`;
  renderStandings('last-run-standings', lastRun.standings, 'No final standings captured.');
}

async function refresh() {
  try {
    const response = await fetch('/api/overlay/tilt', { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const payload = await response.json();
    $('overlay-title').textContent = payload.title || 'MyStats Tilt Run Tracker';

    applyTheme(payload.settings || {});

    const refreshFromPayload = Number(payload.settings?.refresh_seconds || defaultSettings.refresh_seconds);
    const newRefresh = Math.max(1, Math.min(30, refreshFromPayload));
    if (newRefresh !== refreshSeconds) {
      refreshSeconds = newRefresh;
      startRefreshTimer();
    }

    renderCurrentRun(payload.current_run || {});
    renderLastRun(payload.last_run || {});
  } catch (e) {
    $('run-status').textContent = 'Status: Unavailable';
    $('last-run-summary').textContent = 'Unable to load tilt overlay data from /api/overlay/tilt.';
  }
}

function startRefreshTimer() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(refresh, refreshSeconds * 1000);
}

refresh();
startRefreshTimer();
