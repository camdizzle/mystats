const el = (id) => document.getElementById(id);

let activeView = 'mycycle';
let raceDashboardFilter = 'both';
let tiltSortBy = 'tilt_points';
let tiltSortOrder = 'desc';
let rivalsGuideCollapsed = false;

const I18N = {
  en: {},
  es: {
    'Tracked Racers': 'Corredores seguidos',
    'Total Cycles Completed': 'Ciclos completados',
    'Within 2 Positions': 'A 2 posiciones',
    'Cycle Highlights': 'Resumen de ciclos',
    'No cycle completions yet': 'Aún no hay ciclos completados',
    'Top Cycler': 'Mejor ciclista',
    'Newest Cycler': 'Ciclista más reciente',
    'cycles completed': 'ciclos completados',
    'No active session': 'Sin sesión activa',
    'Session': 'Sesión',
    'No MyCycle race data yet.': 'Aún no hay datos de carreras MyCycle.',
    'positions': 'posiciones',
    'Missing': 'Faltan',
    'None': 'Ninguna',
    'Current races': 'Carreras actuales',
    'Last cycle': 'Último ciclo',
    'No season quest data yet.': 'Aún no hay datos de misiones de temporada.',
    'complete': 'completado',
    'Disabled': 'Desactivado',
    'No tilt competitors yet.': 'Aún no hay competidores de tilt.',
    'Death Rate': 'Tasa de muertes',
    'Deaths Today': 'Muertes hoy',
    'Total Tilt Points': 'Puntos Tilt totales',
    'No rivals found. Lower minimum races or increase max point gap in settings.': 'No se encontraron rivales. Baja el mínimo de carreras o aumenta la brecha máxima en ajustes.',
    'No competitors found for this filter.': 'No se encontraron competidores para este filtro.',
    'Updated now': 'Actualizado ahora',
    'Updated': 'Actualizado',
    'Unable to load MyCycle data.': 'No se pudieron cargar los datos de MyCycle.',
  },
  au: {
    'Tracked Racers': 'Tracked Mates on the Track',
    'Total Cycles Completed': 'Total Cycles Knocked Over',
    'Within 2 Positions': 'Within 2 Spots, too right',
    'Cycle Highlights': 'Cycle Highlights, bonza bits',
    'No cycle completions yet': 'No cycle completions yet, give it a tick',
    'Top Cycler': 'Top Cycler, absolute legend',
    'Newest Cycler': 'Newest Cycler on the scene',
    'cycles completed': 'cycles smashed out',
    'No active session': 'No active session right now',
    'Session': 'Session, mate zone',
    'No MyCycle race data yet.': 'No MyCycle race data yet, not a sausage.',
    'positions': 'spots',
    'Missing': 'Still chasing',
    'None': 'Nunya',
    'Current races': 'Current races on the go',
    'Last cycle': 'Last cycle run',
    'No season quest data yet.': 'No season quest data yet, matey.',
    'complete': 'done and dusted',
    'Disabled': 'Switched off',
    'No tilt competitors yet.': 'No tilt competitors yet, waiting on the crew.',
    'Death Rate': 'Death Rate, rough as guts',
    'Deaths Today': 'Deaths Today, crikey count',
    'Total Tilt Points': 'Total Tilt Points, ripper tally',
    'No rivals found. Lower minimum races or increase max point gap in settings.': 'No rivals found. Drop minimum races or widen point gap in settings, mate.',
    'No competitors found for this filter.': 'No competitors for this filter, try another one.',
    'Updated now': 'Updated just now, fresh as',
    'Updated': 'Updated, fresh off the barbie',
    'Unable to load MyCycle data.': 'Could not load MyCycle data, bit crook.',
  }
};

let currentLanguage = 'en';
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
  if (!slang) return 'mate';
  if (!/\bmate\b[.!?]*$/i.test(slang)) {
    slang = slang.replace(/[.!?]+$/, '').trim();
    slang = `${slang}, mate`;
  }
  return slang;
}

const t = (key) => {
  const translated = I18N[currentLanguage]?.[key] || key;
  return currentLanguage === 'au' ? toAussieSlang(translated) : translated;
};

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
    { label: t('Tracked Racers'), value: fmt(racers) },
    { label: t('Total Cycles Completed'), value: fmt(cycles) },
    { label: t('Within 2 Positions'), value: fmt(nearComplete) },
  ].map((kpi) => (
    `<div class="kpi"><div class="kpi-label">${escapeHtml(kpi.label)}</div><div class="kpi-value">${escapeHtml(kpi.value)}</div></div>`
  )).join('');
}


function renderCycleHighlights(rows = []) {
  const host = el('cycle-highlights');
  if (!host) return;

  if (!rows.length) {
    host.innerHTML = `<div class="highlight-card"><div class="highlight-title">${escapeHtml(t('Cycle Highlights'))}</div><div class="highlight-main">${escapeHtml(t('No cycle completions yet'))}</div></div>`;
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
  const newestWhen = newestCycler?.last_cycle_completed_at || t('No cycle completions yet');

  host.innerHTML = [
    `<div class="highlight-card"><div class="highlight-title">${escapeHtml(t('Top Cycler'))}</div><div class="highlight-main">${escapeHtml(topName)}</div><div class="highlight-detail">${escapeHtml(`${fmt(topCycles)} ${t('cycles completed')}`)}</div></div>`,
    `<div class="highlight-card"><div class="highlight-title">${escapeHtml(t('Newest Cycler'))}</div><div class="highlight-main">${escapeHtml(newestName)}</div><div class="highlight-detail">${escapeHtml(newestWhen)}</div></div>`,
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
  const sessionName = data?.mycycle?.session?.name || t('No active session');
  el('mycycle-meta').textContent = `${t('Session')}: ${sessionName}`;
  renderKpis(rows);
  renderCycleHighlights(rows);

  if (!rows.length) {
    rowsHost.innerHTML = `<div class="empty">${escapeHtml(t('No MyCycle race data yet.'))}</div>`;
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
        <div class="subline">${escapeHtml(`${completed}/${total} ${t('positions')} • ${t('Missing')}: ${missing.length ? missing.join(', ') : t('None')} • ${t('Current races')}: ${fmt(row.current_cycle_races)} • ${t('Last cycle')}: ${fmt(row.last_cycle_races)}`)}</div>
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
    { label: t('Tracked Racers'), value: fmt(racers) },
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
    return `<div class="quest-target ${enabled ? '' : 'quest-target--disabled'}"><span>${escapeHtml(label)}</span><strong>${enabled ? escapeHtml(fmt(value)) : t('Disabled')}</strong></div>`;
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
    rowsHost.innerHTML = `<div class="empty">${escapeHtml(t('No season quest data yet.'))}</div>`;
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
          <span class="stat">${escapeHtml(`${completedText} ${t('complete')}`)}</span>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width:${percent}%"></div></div>
        <div class="quest-metrics">
          <span>Points: ${escapeHtml(fmt(row.points))}</span>
          <span>Races: ${escapeHtml(fmt(row.races))}</span>
          <span>Race HS: ${escapeHtml(fmt(row.race_hs))}</span>
          <span>BR HS: ${escapeHtml(fmt(row.br_hs))}</span>
          <span>Tilt Levels: ${escapeHtml(fmt(row.tilt_levels))}</span>
          <span>Top Tiltees: ${escapeHtml(fmt(getTopTilteeCount(row)))}</span>
          <span>Tilt Points: ${escapeHtml(fmt(row.tilt_points))}</span>
        </div>
      </div>
    `;
  }).join('');
}



function getTopTilteeCount(row = {}) {
  if (row == null || typeof row !== 'object') return 0;
  if (row.tilt_top_tiltee != null && row.tilt_top_tiltee !== '') return Number(row.tilt_top_tiltee || 0);
  return Number(row.tilt_tops || 0);
}

function renderTiltKpis(rows = [], data = {}) {
  const host = el('tilt-kpis');
  if (!host) return;

  const totals = data?.tilt?.totals || {};
  const deathsToday = Number(data?.tilt?.deaths_today || 0);
  const totalLevels = Number(totals.levels || 0);
  const totalTopTiltees = Number(totals.top_tiltees ?? totals.tilt_tops ?? 0);
  const totalPoints = Number(totals.points || 0);
  const totalDeaths = Math.max(0, totalLevels - totalTopTiltees);
  const deathRate = totalLevels > 0 ? ((totalDeaths / totalLevels) * 100) : 0;

  host.innerHTML = [
    { label: 'Tilt Competitors', value: fmt(uniqueParticipantCount(rows)) },
    { label: t('Deaths Today'), value: fmt(deathsToday) },
    { label: t('Death Rate'), value: `${deathRate.toFixed(1)}%` },
    { label: t('Total Tilt Points'), value: fmt(totalPoints) },
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
  if (getTopTilteeCount(b) !== getTopTilteeCount(a)) return getTopTilteeCount(b) - getTopTilteeCount(a);
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
    if (getTopTilteeCount(row) !== getTopTilteeCount(best)) {
      return getTopTilteeCount(row) > getTopTilteeCount(best) ? row : best;
    }
    return String(row.display_name || row.username || '').localeCompare(String(best.display_name || best.username || '')) < 0 ? row : best;
  }, null);

  const topTiltee = rows.reduce((best, row) => {
    if (!best) return row;
    if (getTopTilteeCount(row) !== getTopTilteeCount(best)) {
      return getTopTilteeCount(row) > getTopTilteeCount(best) ? row : best;
    }
    return Number(row.tilt_points || 0) > Number(best.tilt_points || 0) ? row : best;
  }, null);

  const leaderName = pointsLeader?.display_name || pointsLeader?.username || '—';
  const topTilteeName = topTiltee?.display_name || topTiltee?.username || '—';

  host.innerHTML = [
    `<div class="highlight-card"><div class="highlight-title">Points Leader</div><div class="highlight-main">${escapeHtml(leaderName)}</div><div class="highlight-detail">${escapeHtml(`${fmt(pointsLeader?.tilt_points || 0)} tilt points`)}</div></div>`,
    `<div class="highlight-card"><div class="highlight-title">Top Tiltee Legend</div><div class="highlight-main">${escapeHtml(topTilteeName)}</div><div class="highlight-detail">${escapeHtml(`${fmt(getTopTilteeCount(topTiltee))} top-tiltee finishes`)}</div></div>`,
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
      const topTiltees = getTopTilteeCount(row);
      const deaths = Math.max(0, tiltLevels - topTiltees);
      const deathRate = tiltLevels > 0 ? (deaths / tiltLevels) * 100 : 0;
      const pressureScore = (Number(row.tilt_points || 0) * 1.5) + (topTiltees * 25) - (deaths * 8);
      const consistency = Math.max(0, 100 - deathRate);

      return {
        ...row,
        tilt_top_tiltee: topTiltees,
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
    rowsHost.innerHTML = `<div class="empty">${escapeHtml(t('No tilt competitors yet.'))}</div>`;
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
          <span>Top Tiltees: ${escapeHtml(fmt(getTopTilteeCount(row)))}</span>
          <span>Death Count: ${escapeHtml(fmt(row.deaths))}</span>
          <span>Death Rate: ${escapeHtml(`${row.death_rate.toFixed(1)}%`)}</span>
          <span>Consistency: ${escapeHtml(`${row.consistency.toFixed(1)}%`)}</span>
        </div>
      </div>
    `;
  }).join('');
}


function getRivalsOnboardingSteps(settings = {}) {
  const minRaces = Math.max(1, Number(settings?.min_races || 0) || 50);
  const maxGap = Math.max(0, Number(settings?.max_point_gap || 0) || 1500);
  const pairCount = Math.max(1, Number(settings?.pair_count || 0) || 25);

  return [
    `1) MyStats scans players with at least ${fmt(minRaces)} season races.`,
    `2) It compares point totals and keeps pairs within a ${fmt(maxGap)}-point gap.`,
    `3) The dashboard ranks the ${fmt(Math.min(200, pairCount))} closest pairs (smaller gap = stronger rivalry).`,
    '4) Use !rivals <name> for personal rivals, or !h2h <name1> <name2> for direct matchups in chat.',
  ];
}

function renderRivalsOnboarding(settings = {}, rows = []) {
  const stepsHost = el('rivals-onboarding-steps');
  const contextHost = el('rivals-onboarding-context');
  if (!stepsHost || !contextHost) return;

  const steps = getRivalsOnboardingSteps(settings);
  stepsHost.innerHTML = steps.map((step) => `<li>${escapeHtml(step)}</li>`).join('');

  if (!rows.length) {
    contextHost.textContent = 'No rivals currently qualify. Try lowering Minimum Season Races or increasing Maximum Point Gap in Settings → Rivals.';
    return;
  }

  const closest = rows[0];
  const closestNames = `${closest.display_a || closest.user_a || 'Player A'} vs ${closest.display_b || closest.user_b || 'Player B'}`;
  contextHost.textContent = `Current closest rivalry: ${closestNames} at ${fmt(closest.point_gap)} points apart.`;
}

function wireRivalsOnboardingToggle() {
  const toggle = el('rivals-onboarding-toggle');
  const panel = el('rivals-onboarding');
  if (!toggle || !panel || toggle.dataset.wired === 'true') return;

  toggle.dataset.wired = 'true';
  toggle.addEventListener('click', () => {
    rivalsGuideCollapsed = !rivalsGuideCollapsed;
    panel.classList.toggle('rivals-onboarding--collapsed', rivalsGuideCollapsed);
    toggle.textContent = rivalsGuideCollapsed ? 'Show guide' : 'Hide guide';
    toggle.setAttribute('aria-expanded', rivalsGuideCollapsed ? 'false' : 'true');
  });
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
  const mostOneSided = rows.reduce((best, row) => {
    if (!best) return row;
    const rowGap = Number(row.point_gap || 0);
    const bestGap = Number(best.point_gap || 0);
    if (rowGap !== bestGap) return rowGap > bestGap ? row : best;

    const rowRaceGap = Math.abs(Number(row.races_a || 0) - Number(row.races_b || 0));
    const bestRaceGap = Math.abs(Number(best.races_a || 0) - Number(best.races_b || 0));
    return rowRaceGap > bestRaceGap ? row : best;
  }, null);

  const closestNames = `${closest.display_a || closest.user_a || '—'} vs ${closest.display_b || closest.user_b || '—'}`;
  const oneSidedNames = `${mostOneSided.display_a || mostOneSided.user_a || '—'} vs ${mostOneSided.display_b || mostOneSided.user_b || '—'}`;

  host.innerHTML = [
    `<div class="highlight-card"><div class="highlight-title">Closest Matchup</div><div class="highlight-main">${escapeHtml(closestNames)}</div><div class="highlight-detail">${escapeHtml(`${fmt(closest.point_gap)} point gap`)}</div></div>`,
    `<div class="highlight-card"><div class="highlight-title">Most One-Sided</div><div class="highlight-main">${escapeHtml(oneSidedNames)}</div><div class="highlight-detail">${escapeHtml(`${fmt(mostOneSided.point_gap)} point gap`)}</div></div>`,
  ].join('');
}

function renderRivalsRows(data) {
  const rowsHost = el('rivals-leaderboard');
  if (!rowsHost) return;

  const rows = Array.isArray(data?.rivals) ? data.rivals : [];

  renderRivalsOnboarding(data?.settings?.rivals || {}, rows);
  renderRivalsKpis(rows);
  renderRivalsHighlights(rows);

  if (!rows.length) {
    rowsHost.innerHTML = `<div class="empty">${escapeHtml(t('No rivals found. Lower minimum races or increase max point gap in settings.'))}</div>`;
    return;
  }

  el('rivals-range-pill').textContent = `Top ${Math.min(200, rows.length)} rivalries`;
  rowsHost.innerHTML = rows.slice(0, 200).map((row, idx) => {
    const pointsA = Number(row.points_a || 0);
    const pointsB = Number(row.points_b || 0);
    const racesA = Number(row.races_a || 0);
    const racesB = Number(row.races_b || 0);
    const gap = Math.abs(pointsA - pointsB);
    const pointDelta = pointsA - pointsB;
    const raceDelta = racesA - racesB;
    const pprA = racesA > 0 ? pointsA / racesA : 0;
    const pprB = racesB > 0 ? pointsB / racesB : 0;
    const pprDelta = pprA - pprB;
    const leaderName = pointDelta >= 0 ? (row.display_a || row.user_a || 'Player A') : (row.display_b || row.user_b || 'Player B');
    const leadValue = Math.abs(pointDelta);

    return `
      <div class="row">
        <div class="row-head">
          <span class="rank">#${idx + 1}</span>
          <span class="name">${escapeHtml(`${row.display_a || row.user_a || '-'} vs ${row.display_b || row.user_b || '-'}`)}</span>
          <span class="stat">${escapeHtml(`${leaderName} +${fmt(leadValue)}`)}</span>
        </div>
        <div class="quest-metrics">
          <span>${escapeHtml(row.display_a || row.user_a || 'Player A')}: ${escapeHtml(fmt(pointsA))} pts (${escapeHtml(fmt(racesA))} races)</span>
          <span>${escapeHtml(row.display_b || row.user_b || 'Player B')}: ${escapeHtml(fmt(pointsB))} pts (${escapeHtml(fmt(racesB))} races)</span>
          <span>Point Gap: ${escapeHtml(fmt(gap))}</span>
          <span>Race Gap: ${escapeHtml(fmt(Math.abs(raceDelta)))}</span>
          <span>PPR Edge: ${escapeHtml((Math.abs(pprDelta)).toFixed(2))} (${escapeHtml((pprDelta >= 0 ? (row.display_a || row.user_a || 'Player A') : (row.display_b || row.user_b || 'Player B')))} ahead)</span>
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
    { label: t('Tracked Racers'), value: fmt(filteredRows.length) },
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
    rowsHost.innerHTML = `<div class="empty">${escapeHtml(t('No competitors found for this filter.'))}</div>`;
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



function getRequestedViewFromLocation() {
  const hashView = String(window.location.hash || '').replace('#', '').trim();
  const validViews = new Set(['mycycle', 'season-quests', 'tilt', 'rivals', 'races']);
  if (validViews.has(hashView)) return hashView;

  const viewFromQuery = new URLSearchParams(window.location.search).get('view');
  return validViews.has(viewFromQuery) ? viewFromQuery : null;
}

function setActiveView(viewName) {
  activeView = viewName;
  if (window.location.hash !== `#${activeView}`) {
    window.history.replaceState(null, '', `#${activeView}`);
  }

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
    currentLanguage = data?.settings?.language || currentLanguage || 'en';
    el('updated-at').textContent = data.updated_at ? `${t('Updated')} ${data.updated_at}` : t('Updated now');
    renderMyCycleRows(data);
    renderSeasonQuestRows(data);
    renderTiltRows(data);
    renderRivalsRows(data);
    renderRaceDashboardRows(data);
  } catch (error) {
    console.error('dashboard refresh failed', error);
    const node = el('mycycle');
    if (node) node.innerHTML = `<div class="empty">${escapeHtml(t('Unable to load MyCycle data.'))}</div>`;
  }
}

const requestedView = getRequestedViewFromLocation();
if (requestedView) {
  setActiveView(requestedView);
}

refresh();
wireViewTabs();
wireRaceFilterButtons();
wireTiltSortControls();
wireRivalsOnboardingToggle();
window.addEventListener('hashchange', () => {
  const hashView = getRequestedViewFromLocation();
  if (hashView) setActiveView(hashView);
});
setInterval(refresh, 15000);
