const el = (id) => document.getElementById(id);

let activeView = 'mycycle';
let raceDashboardFilter = 'both';
let tiltSortBy = 'tilt_points';
let tiltSortOrder = 'desc';

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

function uniqueParticipantCount(rows = []) {
  return new Set(
    rows
      .map((row) => String(row?.display_name || row?.username || '').trim())
      .filter(Boolean)
  ).size;
}

function renderKpis(rows = []) {
  const kpiHost = el('summary-kpis');
  if (!kpiHost) return;

  const racers = uniqueParticipantCount(rows);
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

  const racers = uniqueParticipantCount(rows);
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

  const seasonPayload = data?.season_quests;
  const targets = (!Array.isArray(seasonPayload) && seasonPayload?.targets) || data?.season_quest_targets || {};
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

  const seasonPayload = data?.season_quests;
  const rows = Array.isArray(seasonPayload)
    ? seasonPayload
    : (Array.isArray(seasonPayload?.rows) ? seasonPayload.rows : []);
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


function renderTiltKpis(rows = [], data = {}) {
  const host = el('tilt-kpis');
  if (!host) return;

  const totals = data?.tilt?.totals || {};
  const deathsToday = Number(data?.tilt?.deaths_today || 0);
  const totalLevels = Number(totals.levels || 0);
  const totalPoints = Number(totals.points || 0);
  const deathRate = totalLevels > 0 ? ((deathsToday / totalLevels) * 100) : 0;

  host.innerHTML = [
    { label: 'Tilt Competitors', value: fmt(uniqueParticipantCount(rows)) },
    { label: 'Deaths Today', value: fmt(deathsToday) },
    { label: 'Death Rate', value: `${deathRate.toFixed(1)}%` },
    { label: 'Total Tilt Points', value: fmt(totalPoints) },
  ].map((kpi) => (
    `<div class="kpi"><div class="kpi-label">${escapeHtml(kpi.label)}</div><div class="kpi-value">${escapeHtml(kpi.value)}</div></div>`
  )).join('');
}

function compareTiltRows(a, b, sortBy = 'tilt_points', sortOrder = 'desc') {
  const direction = sortOrder === 'asc' ? 1 : -1;

  if (sortBy === 'name') {
    const nameA = String(a.display_name || a.username || '').toLowerCase();
    const nameB = String(b.display_name || b.username || '').toLowerCase();
    const nameCmp = nameA.localeCompare(nameB);
    if (nameCmp !== 0) return nameCmp * direction;
  } else {
    const valueA = Number(a?.[sortBy] || 0);
    const valueB = Number(b?.[sortBy] || 0);
    if (valueA !== valueB) return (valueA - valueB) * direction;
  }

  if (Number(b.tilt_points || 0) !== Number(a.tilt_points || 0)) return Number(b.tilt_points || 0) - Number(a.tilt_points || 0);
  if (Number(b.tilt_top_tiltee || 0) !== Number(a.tilt_top_tiltee || 0)) return Number(b.tilt_top_tiltee || 0) - Number(a.tilt_top_tiltee || 0);
  return String(a.display_name || a.username || '').localeCompare(String(b.display_name || b.username || ''));
}

function renderTiltHighlights(rows = [], data = {}) {
  const host = el('tilt-highlights');
  if (!host) return;

  if (!rows.length) {
    host.innerHTML = '<div class="highlight-card"><div class="highlight-title">Tilt Highlights</div><div class="highlight-main">No tilt data yet</div></div>';
    return;
  }

  const pointsLeader = rows.reduce((best, row) => {
    if (!best) return row;
    if (Number(row.tilt_points || 0) !== Number(best.tilt_points || 0)) {
      return Number(row.tilt_points || 0) > Number(best.tilt_points || 0) ? row : best;
    }
    if (Number(row.tilt_top_tiltee || 0) !== Number(best.tilt_top_tiltee || 0)) {
      return Number(row.tilt_top_tiltee || 0) > Number(best.tilt_top_tiltee || 0) ? row : best;
    }
    return String(row.display_name || row.username || '').localeCompare(String(best.display_name || best.username || '')) < 0 ? row : best;
  }, null);

  const topTiltee = rows.reduce((best, row) => {
    if (!best) return row;
    if (Number(row.tilt_top_tiltee || 0) !== Number(best.tilt_top_tiltee || 0)) {
      return Number(row.tilt_top_tiltee || 0) > Number(best.tilt_top_tiltee || 0) ? row : best;
    }
    return Number(row.tilt_points || 0) > Number(best.tilt_points || 0) ? row : best;
  }, null);

  const leaderName = pointsLeader?.display_name || pointsLeader?.username || '—';
  const topTilteeName = topTiltee?.display_name || topTiltee?.username || '—';

  host.innerHTML = [
    `<div class="highlight-card"><div class="highlight-title">Points Leader</div><div class="highlight-main">${escapeHtml(leaderName)}</div><div class="highlight-detail">${escapeHtml(`${fmt(pointsLeader?.tilt_points || 0)} tilt points`)}</div></div>`,
    `<div class="highlight-card"><div class="highlight-title">Top Tiltee Legend</div><div class="highlight-main">${escapeHtml(topTilteeName)}</div><div class="highlight-detail">${escapeHtml(`${fmt(topTiltee?.tilt_top_tiltee || 0)} top-tiltee finishes`)}</div></div>`,
  ].join('');
}

function renderTiltRows(data) {
  const rowsHost = el('tilt-leaderboard');
  if (!rowsHost) return;

  const seasonPayload = data?.season_quests;
  const allRows = Array.isArray(seasonPayload)
    ? seasonPayload
    : (Array.isArray(seasonPayload?.rows) ? seasonPayload.rows : []);

  const rows = allRows
    .filter((row) => Number(row.tilt_levels || 0) > 0 || Number(row.tilt_points || 0) > 0)
    .map((row) => {
      const tiltLevels = Number(row.tilt_levels || 0);
      const deaths = Math.max(0, tiltLevels - Number(row.tilt_top_tiltee || 0));
      const deathRate = tiltLevels > 0 ? (deaths / tiltLevels) * 100 : 0;
      const pressureScore = (Number(row.tilt_points || 0) * 1.5) + (Number(row.tilt_top_tiltee || 0) * 25) - (deaths * 8);
      const consistency = Math.max(0, 100 - deathRate);

      return {
        ...row,
        deaths,
        death_rate: deathRate,
        pressure_score: pressureScore,
        consistency,
      };
    })
    .sort((a, b) => compareTiltRows(a, b, tiltSortBy, tiltSortOrder));

  renderTiltKpis(rows, data);
  renderTiltHighlights(rows, data);

  if (!rows.length) {
    rowsHost.innerHTML = '<div class="empty">No tilt competitors yet.</div>';
    return;
  }

  el('tilt-range-pill').textContent = `Top ${Math.min(100, rows.length)}`;
  rowsHost.innerHTML = rows.slice(0, 100).map((row, idx) => {
    return `
      <div class="row">
        <div class="row-head">
          <span class="rank">#${idx + 1}</span>
          <span class="name">${escapeHtml(row.display_name || row.username || '-')}</span>
          <span class="stat">${escapeHtml(tiltSortBy === 'pressure_score' ? `${fmt(Math.round(row.pressure_score))} pressure` : `${fmt(row.tilt_points)} pts`)}</span>
        </div>
        <div class="quest-metrics">
          <span>Tilt Points: ${escapeHtml(fmt(row.tilt_points))}</span>
          <span>Tilt Levels: ${escapeHtml(fmt(row.tilt_levels))}</span>
          <span>Top Tiltees: ${escapeHtml(fmt(row.tilt_top_tiltee))}</span>
          <span>Death Count: ${escapeHtml(fmt(row.deaths))}</span>
          <span>Death Rate: ${escapeHtml(`${row.death_rate.toFixed(1)}%`)}</span>
          <span>Consistency: ${escapeHtml(`${row.consistency.toFixed(1)}%`)}</span>
        </div>
      </div>
    `;
  }).join('');
}


function renderRivalsKpis(rows = []) {
  const host = el('rivals-kpis');
  if (!host) return;

  const uniqueNames = new Set();
  let totalGap = 0;
  let closestGap = null;

  rows.forEach((row) => {
    const nameA = String(row.display_a || row.user_a || '').trim();
    const nameB = String(row.display_b || row.user_b || '').trim();
    if (nameA) uniqueNames.add(nameA);
    if (nameB) uniqueNames.add(nameB);

    const gap = Number(row.point_gap || 0);
    totalGap += gap;
    if (closestGap === null || gap < closestGap) closestGap = gap;
  });

  const avgGap = rows.length ? (totalGap / rows.length) : 0;

  host.innerHTML = [
    { label: 'Rival Pairs', value: fmt(rows.length) },
    { label: 'Unique Rivals', value: fmt(uniqueNames.size) },
    { label: 'Closest Gap', value: fmt(closestGap ?? 0) },
    { label: 'Average Gap', value: fmt(Math.round(avgGap)) },
  ].map((kpi) => (
    `<div class="kpi"><div class="kpi-label">${escapeHtml(kpi.label)}</div><div class="kpi-value">${escapeHtml(kpi.value)}</div></div>`
  )).join('');
}

function renderRivalsHighlights(rows = []) {
  const host = el('rivals-highlights');
  if (!host) return;

  if (!rows.length) {
    host.innerHTML = '<div class="highlight-card"><div class="highlight-title">Rivals Highlights</div><div class="highlight-main">No rivalries found with current settings</div></div>';
    return;
  }

  const closest = rows[0];
  const hottest = rows.reduce((best, row) => {
    if (!best) return row;
    const rowCombined = Number(row.points_a || 0) + Number(row.points_b || 0);
    const bestCombined = Number(best.points_a || 0) + Number(best.points_b || 0);
    if (rowCombined !== bestCombined) return rowCombined > bestCombined ? row : best;
    return Number(row.point_gap || 0) < Number(best.point_gap || 0) ? row : best;
  }, null);

  const closestNames = `${closest.display_a || closest.user_a || '—'} vs ${closest.display_b || closest.user_b || '—'}`;
  const hottestNames = `${hottest.display_a || hottest.user_a || '—'} vs ${hottest.display_b || hottest.user_b || '—'}`;

  host.innerHTML = [
    `<div class="highlight-card"><div class="highlight-title">Closest Matchup</div><div class="highlight-main">${escapeHtml(closestNames)}</div><div class="highlight-detail">${escapeHtml(`${fmt(closest.point_gap)} point gap`)}</div></div>`,
    `<div class="highlight-card"><div class="highlight-title">Highest Stakes</div><div class="highlight-main">${escapeHtml(hottestNames)}</div><div class="highlight-detail">${escapeHtml(`${fmt(Number(hottest.points_a || 0) + Number(hottest.points_b || 0))} combined points`)}</div></div>`,
  ].join('');
}

function renderRivalsRows(data) {
  const rowsHost = el('rivals-leaderboard');
  if (!rowsHost) return;

  const rows = Array.isArray(data?.rivals) ? data.rivals : [];

  renderRivalsKpis(rows);
  renderRivalsHighlights(rows);

  if (!rows.length) {
    rowsHost.innerHTML = '<div class="empty">No rivals found. Lower minimum races or increase max point gap in settings.</div>';
    return;
  }

  el('rivals-range-pill').textContent = `Top ${Math.min(200, rows.length)} rivalries`;
  rowsHost.innerHTML = rows.slice(0, 200).map((row, idx) => {
    const pointsA = Number(row.points_a || 0);
    const pointsB = Number(row.points_b || 0);
    const racesA = Number(row.races_a || 0);
    const racesB = Number(row.races_b || 0);
    const gap = Math.abs(pointsA - pointsB);
    const combined = pointsA + pointsB;
    const racesCombined = racesA + racesB;

    return `
      <div class="row">
        <div class="row-head">
          <span class="rank">#${idx + 1}</span>
          <span class="name">${escapeHtml(`${row.display_a || row.user_a || '-'} vs ${row.display_b || row.user_b || '-'}`)}</span>
          <span class="stat">${escapeHtml(`${fmt(gap)} gap`)}</span>
        </div>
        <div class="quest-metrics">
          <span>${escapeHtml(row.display_a || row.user_a || 'Player A')}: ${escapeHtml(fmt(pointsA))} pts (${escapeHtml(fmt(racesA))} races)</span>
          <span>${escapeHtml(row.display_b || row.user_b || 'Player B')}: ${escapeHtml(fmt(pointsB))} pts (${escapeHtml(fmt(racesB))} races)</span>
          <span>Combined Points: ${escapeHtml(fmt(combined))}</span>
          <span>Combined Races: ${escapeHtml(fmt(racesCombined))}</span>
        </div>
      </div>
    `;
  }).join('');
}


function getRaceRowTotals(row, filterMode = 'both') {
  const raceCount = Number(row.race_count || 0);
  const brCount = Number(row.br_count || 0);
  const racePoints = Number(row.race_points || 0);
  const brPoints = Number(row.br_points || 0);

  if (filterMode === 'race') {
    return {
      events: raceCount,
      points: racePoints,
      highScore: Number(row.race_hs || 0),
      modeLabel: 'Races',
    };
  }

  if (filterMode === 'br') {
    return {
      events: brCount,
      points: brPoints,
      highScore: Number(row.br_hs || 0),
      modeLabel: 'BR',
    };
  }

  return {
    events: raceCount + brCount,
    points: racePoints + brPoints,
    highScore: Math.max(Number(row.race_hs || 0), Number(row.br_hs || 0)),
    modeLabel: 'Both',
  };
}

function renderRaceDashboardKpis(rows = [], filterMode = 'both') {
  const host = el('races-kpis');
  if (!host) return;

  const filteredRows = rows.filter((row) => getRaceRowTotals(row, filterMode).events > 0);
  const totalEvents = filteredRows.reduce((acc, row) => acc + getRaceRowTotals(row, filterMode).events, 0);
  const totalPoints = filteredRows.reduce((acc, row) => acc + getRaceRowTotals(row, filterMode).points, 0);
  const avgPoints = totalEvents > 0 ? (totalPoints / totalEvents) : 0;

  host.innerHTML = [
    { label: 'Tracked Racers', value: fmt(filteredRows.length) },
    { label: filterMode === 'race' ? 'Total Races' : (filterMode === 'br' ? 'Total BRs' : 'Total Events'), value: fmt(totalEvents) },
    { label: 'Total Points', value: fmt(totalPoints) },
    { label: 'Avg Points/Event', value: avgPoints.toFixed(1) },
  ].map((kpi) => (
    `<div class="kpi"><div class="kpi-label">${escapeHtml(kpi.label)}</div><div class="kpi-value">${escapeHtml(kpi.value)}</div></div>`
  )).join('');
}

function renderRaceDashboardHighlights(rows = [], filterMode = 'both') {
  const host = el('races-highlights');
  if (!host) return;

  const filteredRows = rows
    .map((row) => ({ ...row, totals: getRaceRowTotals(row, filterMode) }))
    .filter((row) => row.totals.events > 0)
    .sort((a, b) => {
      if (b.totals.points !== a.totals.points) return b.totals.points - a.totals.points;
      return b.totals.events - a.totals.events;
    });

  if (!filteredRows.length) {
    host.innerHTML = '<div class="highlight-card"><div class="highlight-title">Race Highlights</div><div class="highlight-main">No race data yet for this filter</div></div>';
    return;
  }

  const pointsLeader = filteredRows[0];
  const hsLeader = filteredRows.reduce((best, row) => {
    if (!best) return row;
    if (row.totals.highScore !== best.totals.highScore) return row.totals.highScore > best.totals.highScore ? row : best;
    return row.totals.points > best.totals.points ? row : best;
  }, null);

  host.innerHTML = [
    `<div class="highlight-card"><div class="highlight-title">Points Leader</div><div class="highlight-main">${escapeHtml(pointsLeader.display_name || pointsLeader.username || '—')}</div><div class="highlight-detail">${escapeHtml(`${fmt(pointsLeader.totals.points)} points`)}</div></div>`,
    `<div class="highlight-card"><div class="highlight-title">High Score Leader</div><div class="highlight-main">${escapeHtml(hsLeader.display_name || hsLeader.username || '—')}</div><div class="highlight-detail">${escapeHtml(`${fmt(hsLeader.totals.highScore)} top score`)}</div></div>`,
  ].join('');
}

function renderRaceDashboardRows(data) {
  const rowsHost = el('races-leaderboard');
  if (!rowsHost) return;

  const allRows = Array.isArray(data?.races) ? data.races : [];
  const rows = allRows
    .map((row) => ({ ...row, totals: getRaceRowTotals(row, raceDashboardFilter) }))
    .filter((row) => row.totals.events > 0)
    .sort((a, b) => {
      if (b.totals.points !== a.totals.points) return b.totals.points - a.totals.points;
      if (b.totals.events !== a.totals.events) return b.totals.events - a.totals.events;
      return b.totals.highScore - a.totals.highScore;
    });

  renderRaceDashboardKpis(allRows, raceDashboardFilter);
  renderRaceDashboardHighlights(allRows, raceDashboardFilter);

  const modeLabel = raceDashboardFilter === 'race' ? 'Races' : (raceDashboardFilter === 'br' ? 'BR' : 'Both modes');
  el('races-range-pill').textContent = `${modeLabel} • Top ${Math.min(200, rows.length)}`;

  if (!rows.length) {
    rowsHost.innerHTML = '<div class="empty">No competitors found for this filter.</div>';
    return;
  }

  rowsHost.innerHTML = rows.slice(0, 200).map((row, idx) => {
    const avg = row.totals.events > 0 ? (row.totals.points / row.totals.events) : 0;
    return `
      <div class="row">
        <div class="row-head">
          <span class="rank">#${idx + 1}</span>
          <span class="name">${escapeHtml(row.display_name || row.username || '-')}</span>
          <span class="stat">${escapeHtml(`${fmt(row.totals.points)} pts`)}</span>
        </div>
        <div class="quest-metrics">
          <span>Events: ${escapeHtml(fmt(row.totals.events))}</span>
          <span>Avg/Event: ${escapeHtml(avg.toFixed(1))}</span>
          <span>High Score: ${escapeHtml(fmt(row.totals.highScore))}</span>
          <span>Race: ${escapeHtml(`${fmt(row.race_points)} pts / ${fmt(row.race_count)}`)}</span>
          <span>BR: ${escapeHtml(`${fmt(row.br_points)} pts / ${fmt(row.br_count)}`)}</span>
        </div>
      </div>
    `;
  }).join('');
}

function wireRaceFilterButtons() {
  document.querySelectorAll('.mini-filter-btn[data-race-filter]').forEach((btn) => {
    btn.addEventListener('click', () => {
      raceDashboardFilter = btn.dataset.raceFilter || 'both';
      document.querySelectorAll('.mini-filter-btn[data-race-filter]').forEach((candidate) => {
        candidate.classList.toggle('mini-filter-btn--active', candidate.dataset.raceFilter === raceDashboardFilter);
      });
      refresh();
    });
  });
}

function wireTiltSortControls() {
  const sortBySelect = el('tilt-sort-by');
  const sortOrderSelect = el('tilt-sort-order');
  if (!sortBySelect || !sortOrderSelect) return;

  sortBySelect.value = tiltSortBy;
  sortOrderSelect.value = tiltSortOrder;

  sortBySelect.addEventListener('change', () => {
    tiltSortBy = sortBySelect.value || 'tilt_points';
    refresh();
  });

  sortOrderSelect.addEventListener('change', () => {
    tiltSortOrder = sortOrderSelect.value === 'asc' ? 'asc' : 'desc';
    refresh();
  });
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
    renderTiltRows(data);
    renderRivalsRows(data);
    renderRaceDashboardRows(data);
  } catch (error) {
    console.error('dashboard refresh failed', error);
    const node = el('mycycle');
    if (node) node.innerHTML = '<div class="empty">Unable to load MyCycle data.</div>';
  }
}

refresh();
wireViewTabs();
wireRaceFilterButtons();
wireTiltSortControls();
setInterval(refresh, 15000);
