const el = (id) => document.getElementById(id);

let activeView = 'mycycle';

function fmt(n) {
  const x = Number(n || 0);
  return Number.isFinite(x) ? x.toLocaleString() : '0';
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function renderKpis(rows = []) {
  const kpiHost = el('summary-kpis');
  if (!kpiHost) return;

  const racers = rows.length;
  const cycles = rows.reduce((acc, row) => acc + Number(row.cycles_completed || 0), 0);
  const nearComplete = rows.filter((row) => Number(row.progress_total || 0) - Number(row.progress_hits || 0) <= 2).length;

  kpiHost.innerHTML = [
    { label: 'Tracked Racers', value: fmt(racers) },
    { label: 'Total Cycles Completed', value: fmt(cycles) },
    { label: 'Within 2 Positions', value: fmt(nearComplete) },
  ].map((kpi) => (
    `<div class="kpi"><div class="kpi-label">${escapeHtml(kpi.label)}</div><div class="kpi-value">${escapeHtml(kpi.value)}</div></div>`
  )).join('');
}


function renderCycleHighlights(rows = []) {
  const host = el('cycle-highlights');
  if (!host) return;

  if (!rows.length) {
    host.innerHTML = '<div class="highlight-card"><div class="highlight-title">Cycle Highlights</div><div class="highlight-main">No cycle completions yet</div></div>';
    return;
  }

  const topCycler = rows.reduce((best, row) => {
    if (!best) return row;
    const bestCycles = Number(best.cycles_completed || 0);
    const rowCycles = Number(row.cycles_completed || 0);
    if (rowCycles !== bestCycles) return rowCycles > bestCycles ? row : best;
    return Number(row.progress_hits || 0) > Number(best.progress_hits || 0) ? row : best;
  }, null);

  const newestCycler = rows
    .filter((row) => row.last_cycle_completed_at)
    .sort((a, b) => String(b.last_cycle_completed_at).localeCompare(String(a.last_cycle_completed_at)))[0] || null;

  const topName = topCycler?.display_name || topCycler?.username || '—';
  const topCycles = Number(topCycler?.cycles_completed || 0);
  const newestName = newestCycler?.display_name || newestCycler?.username || '—';
  const newestWhen = newestCycler?.last_cycle_completed_at || 'No completed cycles yet';

  host.innerHTML = [
    `<div class="highlight-card"><div class="highlight-title">Top Cycler</div><div class="highlight-main">${escapeHtml(topName)}</div><div class="highlight-detail">${escapeHtml(`${fmt(topCycles)} cycles completed`)}</div></div>`,
    `<div class="highlight-card"><div class="highlight-title">Newest Cycler</div><div class="highlight-main">${escapeHtml(newestName)}</div><div class="highlight-detail">${escapeHtml(newestWhen)}</div></div>`,
  ].join('');
}

function renderMyCycleRows(data) {
  const rowsHost = el('mycycle');
  if (!rowsHost) return;

  const rows = Array.isArray(data?.mycycle?.rows) ? data.mycycle.rows : [];
  const settings = data?.mycycle?.settings || {};
  const minPlace = Number(settings.min_place || 1);
  const maxPlace = Number(settings.max_place || 10);
  const placementRange = [];
  for (let place = minPlace; place <= maxPlace; place += 1) placementRange.push(place);

  el('range-pill').textContent = `Positions ${minPlace}-${maxPlace}`;
  const sessionName = data?.mycycle?.session?.name || 'No active session';
  el('mycycle-meta').textContent = `Session: ${sessionName}`;
  renderKpis(rows);
  renderCycleHighlights(rows);

  if (!rows.length) {
    rowsHost.innerHTML = '<div class="empty">No MyCycle race data yet.</div>';
    return;
  }

  rowsHost.innerHTML = rows.slice(0, 120).map((row, idx) => {
    const hits = new Set(Array.isArray(row.placement_hits) ? row.placement_hits.map((x) => Number(x)) : []);
    const chips = placementRange.map((place) => {
      const hit = hits.has(place);
      return `<span class="pos-chip ${hit ? 'pos-chip--hit' : 'pos-chip--miss'}">${place}</span>`;
    }).join('');

    const completed = Number(row.progress_hits || 0);
    const total = Math.max(1, Number(row.progress_total || 1));
    const percent = Math.max(0, Math.min(100, Number(row.progress_percent ?? ((completed / total) * 100))));
    const missing = Array.isArray(row.missing_places) ? row.missing_places : [];

    return `
      <div class="row">
        <div class="row-head">
          <span class="rank">#${idx + 1}</span>
          <span class="name">${escapeHtml(row.display_name || row.username || '-')}</span>
          <span class="stat">${escapeHtml(`${fmt(row.cycles_completed)} cycles`)}</span>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width:${percent}%"></div></div>
        <div class="positions">${chips}</div>
        <div class="subline">${escapeHtml(`${completed}/${total} positions • Missing: ${missing.length ? missing.join(', ') : 'None'} • Current races: ${fmt(row.current_cycle_races)} • Last cycle: ${fmt(row.last_cycle_races)}`)}</div>
      </div>
    `;
  }).join('');
}

function renderSeasonKpis(rows = []) {
  const host = el('season-kpis');
  if (!host) return;

  const racers = rows.length;
  const completedAll = rows.filter((row) => Number(row.active_quests || 0) > 0 && Number(row.completed || 0) >= Number(row.active_quests || 0)).length;
  const totalCompleted = rows.reduce((acc, row) => acc + Number(row.completed || 0), 0);

  host.innerHTML = [
    { label: 'Tracked Racers', value: fmt(racers) },
    { label: 'All Quests Complete', value: fmt(completedAll) },
    { label: 'Total Quest Clears', value: fmt(totalCompleted) },
  ].map((kpi) => (
    `<div class="kpi"><div class="kpi-label">${escapeHtml(kpi.label)}</div><div class="kpi-value">${escapeHtml(kpi.value)}</div></div>`
  )).join('');
}

function renderSeasonTargets(data) {
  const host = el('season-quest-targets');
  if (!host) return;

  const targets = data?.season_quests?.targets || {};
  const questCards = [
    ['Season Races', targets.races],
    ['Season Points', targets.points],
    ['Race HS', targets.race_hs],
    ['BR HS', targets.br_hs],
    ['Tilt Levels', targets.tilt_levels],
    ['Top Tiltees', targets.tilt_tops],
    ['Tilt Points', targets.tilt_points],
  ];

  host.innerHTML = questCards.map(([label, value]) => {
    const enabled = Number(value || 0) > 0;
    return `<div class="quest-target ${enabled ? '' : 'quest-target--disabled'}"><span>${escapeHtml(label)}</span><strong>${enabled ? escapeHtml(fmt(value)) : 'Disabled'}</strong></div>`;
  }).join('');
}

function renderSeasonQuestRows(data) {
  const rowsHost = el('season-quests');
  if (!rowsHost) return;

  const rows = Array.isArray(data?.season_quests?.rows) ? data.season_quests.rows : [];
  renderSeasonKpis(rows);
  renderSeasonTargets(data);

  if (!rows.length) {
    rowsHost.innerHTML = '<div class="empty">No season quest data yet.</div>';
    return;
  }

  rowsHost.innerHTML = rows.map((row, idx) => {
    const completed = Number(row.completed || 0);
    const activeQuests = Math.max(1, Number(row.active_quests || 0));
    const percent = Math.max(0, Math.min(100, (completed / activeQuests) * 100));
    const completedText = `${completed}/${Number(row.active_quests || 0)}`;

    return `
      <div class="row">
        <div class="row-head">
          <span class="rank">#${idx + 1}</span>
          <span class="name">${escapeHtml(row.display_name || row.username || '-')}</span>
          <span class="stat">${escapeHtml(`${completedText} complete`)}</span>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width:${percent}%"></div></div>
        <div class="quest-metrics">
          <span>Points: ${escapeHtml(fmt(row.points))}</span>
          <span>Races: ${escapeHtml(fmt(row.races))}</span>
          <span>Race HS: ${escapeHtml(fmt(row.race_hs))}</span>
          <span>BR HS: ${escapeHtml(fmt(row.br_hs))}</span>
          <span>Tilt Levels: ${escapeHtml(fmt(row.tilt_levels))}</span>
          <span>Top Tiltees: ${escapeHtml(fmt(row.tilt_top_tiltee))}</span>
          <span>Tilt Points: ${escapeHtml(fmt(row.tilt_points))}</span>
        </div>
      </div>
    `;
  }).join('');
}

function setActiveView(viewName) {
  activeView = viewName;
  document.querySelectorAll('.dashboard-nav-btn[data-view]').forEach((btn) => {
    const isActive = btn.dataset.view === activeView;
    btn.classList.toggle('dashboard-nav-btn--active', isActive);
  });

  document.querySelectorAll('[data-panel]').forEach((panel) => {
    panel.classList.toggle('is-hidden', panel.dataset.panel !== activeView);
  });
}

function wireViewTabs() {
  document.querySelectorAll('.dashboard-nav-btn[data-view]').forEach((btn) => {
    btn.addEventListener('click', () => setActiveView(btn.dataset.view));
  });
}

async function refresh() {
  try {
    const resp = await fetch('/api/dashboard/main', { cache: 'no-store' });
    const data = await resp.json();
    el('updated-at').textContent = data.updated_at ? `Updated ${data.updated_at}` : 'Updated now';
    renderMyCycleRows(data);
    renderSeasonQuestRows(data);
  } catch (error) {
    console.error('dashboard refresh failed', error);
    const node = el('mycycle');
    if (node) node.innerHTML = '<div class="empty">Unable to load MyCycle data.</div>';
  }
}

refresh();
wireViewTabs();
setInterval(refresh, 15000);
