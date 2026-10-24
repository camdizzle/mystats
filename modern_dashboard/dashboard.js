const el = (id) => document.getElementById(id);

let activeView = 'mycycle';
let raceDashboardFilter = 'both';
let teamLeaderboardFilter = 'season';
let tiltSortBy = 'tilt_points';
let tiltSortOrder = 'desc';
let rivalsSortBy = 'closest';
let rivalsSearchQuery = '';
let rivalsGapPreset = 'all';
let rivalsRowsSnapshot = [];
let rivalsSettingsSnapshot = {};
let mycyclePage = 1;
let mycyclePageSize = 120;
let mycycleQuery = '';
let seasonPage = 1;
let seasonPageSize = 100;
let seasonQuery = '';
let seasonSortBy = 'completed';
let seasonSortOrder = 'desc';
let refreshIntervalHandle = null;
let dashboardStream = null;
let dashboardStreamReconnectTimer = null;
let dashboardStreamQuery = '';

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
    'Season Races': 'Carreras de temporada',
    'Season Points': 'Puntos de temporada',
    'Race HS': 'Récord de carrera',
    'BR HS': 'Récord BR',
    'Tilt Levels': 'Niveles Tilt',
    'Top Tiltees': 'Top Tiltees',
    'Tilt Points': 'Puntos Tilt',
    'No tilt competitors yet.': 'Aún no hay competidores de tilt.',
    'Death Rate': 'Tasa de muertes',
    'Deaths Today': 'Muertes hoy',
    'Total Tilt Points': 'Puntos Tilt totales',
    'No rivals found. Lower minimum races or increase max point gap in settings.': 'No se encontraron rivales. Baja el mínimo de carreras o aumenta la brecha máxima en ajustes.',
    'No competitors found for this filter.': 'No se encontraron competidores para este filtro.',
    'Updated now': 'Actualizado ahora',
    'Updated': 'Actualizado',
    'Unable to load MyStats data.': 'No se pudieron cargar los datos de MyStats.',
    'No rivals currently qualify. Try lowering Minimum Season Races or increasing Maximum Point Gap in Settings → Rivals.': 'No hay rivales que califiquen ahora. Baja Carreras mínimas o sube Brecha máxima en Ajustes → Rivals.',
    'Current closest rivalry': 'Rivalidad más cercana actual',
    'Rivals Highlights': 'Resumen de rivales',
    'No rivalries found with current settings': 'No se encontraron rivalidades con la configuración actual',
    'Closest Matchup': 'Enfrentamiento más parejo',
    'Most One-Sided': 'Más desigual',
    'point gap': 'brecha de puntos',
    'Most One-Sided = largest point gap. Tie-breaker: larger race gap.': 'Más desigual = mayor brecha de puntos. Desempate: mayor brecha de carreras.',
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
    'Season Races': 'Season Races',
    'Season Points': 'Season Points',
    'Race HS': 'Race HS',
    'BR HS': 'BR HS',
    'Tilt Levels': 'Tilt Levels',
    'Top Tiltees': 'Top Tiltees',
    'Tilt Points': 'Tilt Points',
    'No tilt competitors yet.': 'No tilt competitors yet, waiting on the crew.',
    'Death Rate': 'Death Rate, rough as guts',
    'Deaths Today': 'Deaths Today, crikey count',
    'Total Tilt Points': 'Total Tilt Points, ripper tally',
    'No rivals found. Lower minimum races or increase max point gap in settings.': 'No rivals found. Drop minimum races or widen point gap in settings, mate.',
    'No competitors found for this filter.': 'No competitors for this filter, try another one.',
    'Updated now': 'Updated just now, fresh as',
    'Updated': 'Updated, fresh off the barbie',
    'Unable to load MyStats data.': 'Could not load MyStats data, bit crook.',
    'No rivals currently qualify. Try lowering Minimum Season Races or increasing Maximum Point Gap in Settings → Rivals.': 'No rivals qualify right now. Lower min races or lift max gap in Settings → Rivals, mate.',
    'Current closest rivalry': 'Current closest rivalry',
    'Rivals Highlights': 'Rivals Highlights',
    'No rivalries found with current settings': 'No rivalries with current settings, mate',
    'Closest Matchup': 'Closest Matchup',
    'Most One-Sided': 'Most One-Sided',
    'point gap': 'point gap',
    'Most One-Sided = largest point gap. Tie-breaker: larger race gap.': 'Most One-Sided = biggest point gap. Tie-breaker: bigger race gap.',
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


function podiumClassForRank(rank = 0) {
  if (rank === 1) return 'rank--gold';
  if (rank === 2) return 'rank--silver';
  if (rank === 3) return 'rank--bronze';
  return '';
}

function renderRankBadge(rank = 0) {
  const safeRank = Math.max(1, Number(rank || 0));
  const podiumClass = podiumClassForRank(safeRank);
  return `<span class="rank ${podiumClass}">#${safeRank}</span>`;
}

function renderTeamIcon(row = {}) {
  const iconUrl = String(row?.icon_url || '').trim();
  const iconFallback = String(row?.icon || '🏁').trim() || '🏁';
  if (iconUrl) {
    return `<img class="team-icon-image" src="${escapeHtml(iconUrl)}" alt="${escapeHtml(iconFallback)}" loading="lazy" decoding="async">`;
  }
  return `<span class="team-icon-text">${escapeHtml(iconFallback)}</span>`;
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
    .filter((row) => row.last_cycle_completed_at_iso || row.last_cycle_completed_at)
    .sort((a, b) => {
      const left = Number(a.last_cycle_completed_at_epoch || 0);
      const right = Number(b.last_cycle_completed_at_epoch || 0);
      if (left !== right) return right - left;
      return String(b.last_cycle_completed_at || '').localeCompare(String(a.last_cycle_completed_at || ''));
    })[0] || null;

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
  const pageInfo = data?.mycycle?.pagination || null;
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

  const pager = pageInfo ? `
    <div class="subline" style="margin-bottom:8px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
      <input id="mycycle-search" type="text" placeholder="Filter racer" value="${escapeHtml(mycycleQuery)}" style="padding:6px 8px;border-radius:6px;border:1px solid #3d4b63;background:#0f1724;color:#e8eef8;" />
      <button id="mycycle-search-btn" type="button">Apply</button>
      <button id="mycycle-prev" type="button" ${pageInfo.page <= 1 ? 'disabled' : ''}>Prev</button>
      <button id="mycycle-next" type="button" ${pageInfo.page >= pageInfo.total_pages ? 'disabled' : ''}>Next</button>
      <span>${escapeHtml(`Page ${pageInfo.page}/${pageInfo.total_pages} • ${pageInfo.total} racers`)}</span>
    </div>
  ` : '';

  if (!rows.length) {
    rowsHost.innerHTML = `${pager}<div class="empty">${escapeHtml(t('No MyCycle race data yet.'))}</div>`;
    return;
  }

  rowsHost.innerHTML = pager + rows.map((row, idx) => {
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
          ${renderRankBadge(idx + 1 + ((pageInfo?.page || 1) - 1) * (pageInfo?.page_size || rows.length))}
          <span class="name">${escapeHtml(row.display_name || row.username || '-')}</span>
          <span class="stat">${escapeHtml(`${fmt(row.cycles_completed)} cycles`)}</span>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width:${percent}%"></div></div>
        <div class="positions">${chips}</div>
        <div class="subline">${escapeHtml(`${completed}/${total} ${t('positions')} • ${t('Missing')}: ${missing.length ? missing.join(', ') : t('None')} • ${t('Current races')}: ${fmt(row.current_cycle_races)} • ${t('Last cycle')}: ${fmt(row.last_cycle_races)}`)}</div>
      </div>
    `;
  }).join('');

  const searchInput = el('mycycle-search');
  const searchBtn = el('mycycle-search-btn');
  const prevBtn = el('mycycle-prev');
  const nextBtn = el('mycycle-next');
  if (searchBtn && searchInput) {
    searchBtn.onclick = () => {
      mycycleQuery = String(searchInput.value || '').trim();
      mycyclePage = 1;
      refresh();
    };
  }
  if (prevBtn) {
    prevBtn.onclick = () => {
      mycyclePage = Math.max(1, mycyclePage - 1);
      refresh();
    };
  }
  if (nextBtn && pageInfo) {
    nextBtn.onclick = () => {
      mycyclePage = Math.min(pageInfo.total_pages || mycyclePage, mycyclePage + 1);
      refresh();
    };
  }
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
  const targets = (!Array.isArray(seasonPayload) && seasonPayload?.targets) || {};
  const questCards = [
    [t('Season Races'), targets.races],
    [t('Season Points'), targets.points],
    [t('Race HS'), targets.race_hs],
    [t('BR HS'), targets.br_hs],
    [t('Tilt Levels'), targets.tilt_levels],
    [t('Top Tiltees'), targets.tilt_tops],
    [t('Tilt Points'), targets.tilt_points],
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

  const seasonPagination = (!Array.isArray(seasonPayload) && seasonPayload?.pagination) || null;
  const seasonRangePill = el('season-range-pill');
  if (seasonRangePill) {
    if (seasonPagination) {
      seasonRangePill.textContent = `Showing ${fmt(rows.length)} of ${fmt(seasonPagination.total || rows.length)}`;
    } else {
      seasonRangePill.textContent = `Top ${fmt(rows.length)}`;
    }
  }
  wireSeasonPaginationControls(seasonPagination);

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
          ${renderRankBadge(idx + 1 + ((seasonPagination?.page || 1) - 1) * (seasonPagination?.page_size || 100))}
          <span class="name">${escapeHtml(row.display_name || row.username || '-')}</span>
          <span class="stat">${escapeHtml(`${completedText} ${t('complete')}`)}</span>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width:${percent}%"></div></div>
        <div class="quest-metrics">
          <span>${escapeHtml(t('Season Points'))}: ${escapeHtml(fmt(row.points))}</span>
          <span>${escapeHtml(t('Season Races'))}: ${escapeHtml(fmt(row.races))}</span>
          <span>${escapeHtml(t('Race HS'))}: ${escapeHtml(fmt(row.race_hs))}</span>
          <span>${escapeHtml(t('BR HS'))}: ${escapeHtml(fmt(row.br_hs))}</span>
          <span>${escapeHtml(t('Tilt Levels'))}: ${escapeHtml(fmt(row.tilt_levels))}</span>
          <span>${escapeHtml(t('Top Tiltees'))}: ${escapeHtml(fmt(getTopTilteeCount(row)))}</span>
          <span>${escapeHtml(t('Tilt Points'))}: ${escapeHtml(fmt(row.tilt_points))}</span>
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
  const totalDeaths = Number(totals.deaths || 0);
  const knownOutcomes = Number(totals.known_outcomes || 0);
  const deathRate = knownOutcomes > 0 ? (totalDeaths / knownOutcomes) * 100 : null;

  host.innerHTML = [
    { label: 'Tilt Competitors', value: fmt(uniqueParticipantCount(rows)) },
    { label: 'Recorded deaths · selected scope', value: knownOutcomes ? fmt(totalDeaths) : 'Unknown' },
    { label: t('Death Rate'), value: deathRate === null ? 'Unknown' : `${deathRate.toFixed(1)}%` },
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

  const tiltPayload = data?.tilt || {};
  const allRows = Array.isArray(tiltPayload?.leaderboard) ? tiltPayload.leaderboard : [];

  const rows = allRows
    .filter((row) => Number(row.tilt_levels || 0) > 0 || Number(row.tilt_points || 0) > 0)
    .map((row) => {
      const tiltLevels = Number(row.tilt_levels || 0);
      const topTiltees = getTopTilteeCount(row);
      const deaths = Number(row.tilt_deaths || 0);
      const deathRate = Number(row.known_outcomes) > 0 ? (deaths / Number(row.known_outcomes)) * 100 : 0;
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
          ${renderRankBadge(idx + 1)}
          <span class="name">${escapeHtml(row.display_name || row.username || '-')}</span>
          <span class="stat">${escapeHtml(tiltSortBy === 'pressure_score' ? `${fmt(Math.round(row.pressure_score))} pressure` : `${fmt(row.tilt_points)} pts`)}</span>
        </div>
        <div class="quest-metrics">
          <span>Tilt Levels: ${escapeHtml(fmt(row.tilt_levels))}</span>
          <span>Tilt Points: ${escapeHtml(fmt(row.tilt_points))}</span>
          <span>Top Tiltees: ${escapeHtml(fmt(getTopTilteeCount(row)))}</span>
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
    host.innerHTML = `<div class="highlight-card"><div class="highlight-title">${escapeHtml(t('Rivals Highlights'))}</div><div class="highlight-main">${escapeHtml(t('No rivalries found with current settings'))}</div></div>`;
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
    `<div class="highlight-card"><div class="highlight-title">${escapeHtml(t('Closest Matchup'))}</div><div class="highlight-main">${escapeHtml(closestNames)}</div><div class="highlight-detail">${escapeHtml(`${fmt(closest.point_gap)} ${t('point gap')}`)}</div></div>`,
    `<div class="highlight-card" title="${escapeHtml(t('Most One-Sided = largest point gap. Tie-breaker: larger race gap.'))}"><div class="highlight-title">${escapeHtml(t('Most One-Sided'))}</div><div class="highlight-main">${escapeHtml(oneSidedNames)}</div><div class="highlight-detail">${escapeHtml(`${fmt(mostOneSided.point_gap)} ${t('point gap')}`)}</div></div>`,
  ].join('');
}

function getFilteredSortedRivalRows(rows = []) {
  const trimmedQuery = rivalsSearchQuery.trim().toLowerCase();
  const gapLimit = rivalsGapPreset === 'all' ? Number.POSITIVE_INFINITY : Number(rivalsGapPreset || 0);

  const filtered = rows.filter((row) => {
    const rowGap = Number(row.point_gap || 0);
    if (Number.isFinite(gapLimit) && rowGap > gapLimit) return false;
    if (!trimmedQuery) return true;
    const nameA = String(row.display_a || row.user_a || '').toLowerCase();
    const nameB = String(row.display_b || row.user_b || '').toLowerCase();
    return nameA.includes(trimmedQuery) || nameB.includes(trimmedQuery);
  });

  const sorted = [...filtered].sort((a, b) => {
    const pointsA = Number(a.points_a || 0);
    const pointsB = Number(a.points_b || 0);
    const racesA = Number(a.races_a || 0);
    const racesB = Number(a.races_b || 0);
    const gapA = Math.abs(pointsA - pointsB);

    const pointsC = Number(b.points_a || 0);
    const pointsD = Number(b.points_b || 0);
    const racesC = Number(b.races_a || 0);
    const racesD = Number(b.races_b || 0);
    const gapB = Math.abs(pointsC - pointsD);

    if (rivalsSortBy === 'widest') return gapB - gapA;
    if (rivalsSortBy === 'most-races') return (racesC + racesD) - (racesA + racesB);
    if (rivalsSortBy === 'best-ppr') {
      const pprEdgeA = Math.abs((racesA > 0 ? pointsA / racesA : 0) - (racesB > 0 ? pointsB / racesB : 0));
      const pprEdgeB = Math.abs((racesC > 0 ? pointsC / racesC : 0) - (racesD > 0 ? pointsD / racesD : 0));
      return pprEdgeB - pprEdgeA;
    }
    if (rivalsSortBy === 'score') return Number(b.rivalry_score || 0) - Number(a.rivalry_score || 0);
    return gapA - gapB;
  });

  return sorted;
}

function exportRivalsCsv() {
  if (!rivalsRowsSnapshot.length) return;
  const headers = ['rank', 'player_a', 'points_a', 'races_a', 'player_b', 'points_b', 'races_b', 'point_gap', 'recent_point_gap_30d', 'trend', 'rivalry_score'];
  const lines = [headers.join(',')];
  rivalsRowsSnapshot.forEach((row, idx) => {
    lines.push([
      idx + 1,
      row.display_a || row.user_a || '',
      Number(row.points_a || 0),
      Number(row.races_a || 0),
      row.display_b || row.user_b || '',
      Number(row.points_b || 0),
      Number(row.races_b || 0),
      Number(row.point_gap || 0),
      Number(row.recent_point_gap_30d || 0),
      row.trend_direction || 'steady',
      Number(row.rivalry_score || 0),
    ].map((value) => `"${String(value).replace(/"/g, '""')}"`).join(','));
  });

  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `rivals_${new Date().toISOString().slice(0, 19).replace(/[T:]/g, '-')}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function wireRivalsControls() {
  const search = el('rivals-search');
  const sort = el('rivals-sort');
  const preset = el('rivals-preset');
  const exportBtn = el('rivals-export');
  if (!search || !sort || !preset || !exportBtn || search.dataset.wired === 'true') return;

  search.dataset.wired = 'true';
  sort.value = rivalsSortBy;
  preset.value = rivalsGapPreset;

  search.addEventListener('input', () => {
    rivalsSearchQuery = search.value || '';
    renderRivalsRows({ rivals: rivalsRowsSnapshot, settings: rivalsSettingsSnapshot });
  });
  sort.addEventListener('change', () => {
    rivalsSortBy = sort.value || 'closest';
    renderRivalsRows({ rivals: rivalsRowsSnapshot, settings: rivalsSettingsSnapshot });
  });
  preset.addEventListener('change', () => {
    rivalsGapPreset = preset.value || 'all';
    renderRivalsRows({ rivals: rivalsRowsSnapshot, settings: rivalsSettingsSnapshot });
  });
  exportBtn.addEventListener('click', exportRivalsCsv);
}

function renderRivalsRows(data) {
  const rowsHost = el('rivals-leaderboard');
  if (!rowsHost) return;

  const incomingRows = Array.isArray(data?.rivals) ? data.rivals : [];
  rivalsSettingsSnapshot = data?.settings || rivalsSettingsSnapshot;
  rivalsRowsSnapshot = incomingRows;
  const rows = getFilteredSortedRivalRows(rivalsRowsSnapshot);
  wireRivalsControls();

  const rivalsSettings = {
    ...(data?.settings?.rivals || {}),
    max_pairs: Number(data?.settings?.rivals_limits?.max_pairs || 200),
  };

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
          ${renderRankBadge(idx + 1)}
          <span class="name"><button class="player-link" data-player="${escapeHtml(row.user_a)}">${escapeHtml(row.display_a || row.user_a || '-')}</button> vs <button class="player-link" data-player="${escapeHtml(row.user_b)}">${escapeHtml(row.display_b || row.user_b || '-')}</button></span>
          <span class="stat">${escapeHtml(`${leaderName} +${fmt(leadValue)}`)}</span>
        </div>
        <details><summary>Compare matchup</summary><div class="quest-metrics">
          <span>${escapeHtml(row.display_a || row.user_a || 'Player A')}: ${escapeHtml(fmt(pointsA))} pts (${escapeHtml(fmt(racesA))} races)</span>
          <span>${escapeHtml(row.display_b || row.user_b || 'Player B')}: ${escapeHtml(fmt(pointsB))} pts (${escapeHtml(fmt(racesB))} races)</span>
          <span>Point Gap: ${escapeHtml(fmt(gap))}</span>
          <span>Race Gap: ${escapeHtml(fmt(Math.abs(raceDelta)))}</span>
          <span>PPR Edge: ${escapeHtml((Math.abs(pprDelta)).toFixed(2))} (${escapeHtml((pprDelta >= 0 ? (row.display_a || row.user_a || 'Player A') : (row.display_b || row.user_b || 'Player B')))} ahead)</span>
        </div></details>
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

function getRaceFilterLabels(filterMode = 'both') {
  if (filterMode === 'race') {
    return {
      totalLabel: 'Total Races',
      countLabel: 'Races',
      avgLabel: 'Avg Points/Race',
      rowAvgLabel: 'Avg/Race',
    };
  }
  if (filterMode === 'br') {
    return {
      totalLabel: 'Total BRs',
      countLabel: 'BRs',
      avgLabel: 'Avg Points/BR',
      rowAvgLabel: 'Avg/BR',
    };
  }
  return {
    totalLabel: 'Total Races',
    countLabel: 'Races',
    avgLabel: 'Avg Points/Race',
    rowAvgLabel: 'Avg/Race',
  };
}

function renderRaceDashboardKpis(rows = [], filterMode = 'both', payload = null) {
  const host = el('races-kpis');
  if (!host) return;

  const labels = getRaceFilterLabels(filterMode);
  const filteredRows = rows.filter((row) => getRaceRowTotals(row, filterMode).events > 0);
  const dedupedTotals = {
    both: Number(payload?.race_totals?.total_events || 0),
    race: Number(payload?.race_totals?.race_events || 0),
    br: Number(payload?.race_totals?.br_events || 0),
  };
  const fallbackTotalRaces = filteredRows.reduce((acc, row) => acc + getRaceRowTotals(row, filterMode).events, 0);
  const totalRaces = dedupedTotals[filterMode] || fallbackTotalRaces;
  const totalPoints = filteredRows.reduce((acc, row) => acc + getRaceRowTotals(row, filterMode).points, 0);
  const avgPoints = totalRaces > 0 ? (totalPoints / totalRaces) : 0;

  host.innerHTML = [
    { label: t('Tracked Racers'), value: fmt(filteredRows.length) },
    { label: labels.totalLabel, value: fmt(totalRaces) },
    { label: 'Total Points', value: fmt(totalPoints) },
    { label: labels.avgLabel, value: avgPoints.toFixed(1) },
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

  renderRaceDashboardKpis(allRows, raceDashboardFilter, data);
  renderRaceDashboardHighlights(allRows, raceDashboardFilter);

  const modeLabel = raceDashboardFilter === 'race' ? 'Races' : (raceDashboardFilter === 'br' ? 'BR' : 'Both modes');
  el('races-range-pill').textContent = `${modeLabel} • Top ${Math.min(200, rows.length)}`;

  if (!rows.length) {
    rowsHost.innerHTML = `<div class="empty">${escapeHtml(t('No competitors found for this filter.'))}</div>`;
    return;
  }

  const labels = getRaceFilterLabels(raceDashboardFilter);
  rowsHost.innerHTML = rows.slice(0, 200).map((row, idx) => {
    const avg = row.totals.events > 0 ? (row.totals.points / row.totals.events) : 0;
    return `
      <div class="row">
        <div class="row-head">
          ${renderRankBadge(idx + 1)}
          <span class="name">${escapeHtml(row.display_name || row.username || '-')}</span>
          <span class="stat">${escapeHtml(`${fmt(row.totals.points)} pts`)}</span>
        </div>
        <div class="quest-metrics">
          <span>${escapeHtml(labels.countLabel)}: ${escapeHtml(fmt(row.totals.events))}</span>
          <span>${escapeHtml(labels.rowAvgLabel)}: ${escapeHtml(avg.toFixed(1))}</span>
          <span>High Score: ${escapeHtml(fmt(row.totals.highScore))}</span>
          <span>Race: ${escapeHtml(`${fmt(row.race_points)} pts / ${fmt(row.race_count)}`)}</span>
          <span>BR: ${escapeHtml(`${fmt(row.br_points)} pts / ${fmt(row.br_count)}`)}</span>
        </div>
      </div>
    `;
  }).join('');
}




function getTeamRowsByFilter(data, filterMode = 'season') {
  const teams = data?.teams || {};
  if (filterMode === 'daily') return Array.isArray(teams.top_daily) ? teams.top_daily : [];
  if (filterMode === 'weekly') return Array.isArray(teams.top_weekly) ? teams.top_weekly : [];
  return Array.isArray(teams.top_season) ? teams.top_season : [];
}

function renderTeamsKpis(rows = []) {
  const host = el('teams-kpis');
  if (!host) return;

  const recruiting = rows.filter((row) => Boolean(row?.recruiting)).length;
  const avgPoints = rows.length
    ? rows.reduce((acc, row) => acc + Number(row?.points || 0), 0) / rows.length
    : 0;

  host.innerHTML = [
    { label: 'Tracked Teams', value: fmt(rows.length) },
    { label: 'Recruiting Teams', value: fmt(recruiting) },
    { label: 'Avg Team Points', value: fmt(Math.round(avgPoints)) },
  ].map((kpi) => (
    `<div class="kpi"><div class="kpi-label">${escapeHtml(kpi.label)}</div><div class="kpi-value">${escapeHtml(kpi.value)}</div></div>`
  )).join('');
}

function renderTeamsHighlights(rows = []) {
  const host = el('teams-highlights');
  if (!host) return;
  if (!rows.length) {
    host.innerHTML = `<div class="empty">${escapeHtml('No team data yet.')}</div>`;
    return;
  }

  const pointsLeader = rows[0];
  const biggestTeam = rows.reduce((best, row) => {
    if (!best) return row;
    if (Number(row?.size || 0) !== Number(best?.size || 0)) return Number(row?.size || 0) > Number(best?.size || 0) ? row : best;
    return Number(row?.points || 0) > Number(best?.points || 0) ? row : best;
  }, null);

  host.innerHTML = [
    `<div class="highlight-card"><div class="highlight-title">Points Leader</div><div class="highlight-main">${escapeHtml(pointsLeader?.name || '—')}</div><div class="highlight-detail">${escapeHtml(`${fmt(pointsLeader?.points || 0)} pts`)}</div></div>`,
    `<div class="highlight-card"><div class="highlight-title">Largest Team</div><div class="highlight-main">${escapeHtml(biggestTeam?.name || '—')}</div><div class="highlight-detail">${escapeHtml(`${fmt(biggestTeam?.size || 0)} members`)}</div></div>`,
  ].join('');
}

function renderTeamsRows(data) {
  const rowsHost = el('teams-leaderboard');
  if (!rowsHost) return;

  const rows = getTeamRowsByFilter(data, teamLeaderboardFilter);
  renderTeamsKpis(rows);
  renderTeamsHighlights(rows);

  const label = teamLeaderboardFilter === 'daily' ? 'Daily' : (teamLeaderboardFilter === 'weekly' ? 'Weekly' : 'Season');
  const rangePill = el('teams-range-pill');
  if (rangePill) rangePill.textContent = `${label} • Top ${Math.min(100, rows.length)}`;

  if (!rows.length) {
    rowsHost.innerHTML = `<div class="empty">${escapeHtml('No teams found.')}</div>`;
    return;
  }

  rowsHost.innerHTML = rows.slice(0, 100).map((row, idx) => `
    <div class="row">
      <div class="row-head">
        ${renderRankBadge(idx + 1)}
        <span class="name team-name"><span class="team-icon">${renderTeamIcon(row)}</span>${escapeHtml(row?.name || '-')}</span>
        <span class="stat">${escapeHtml(`${fmt(row?.points || 0)} pts`)}</span>
      </div>
      <div class="quest-metrics">
        <span>Captain: ${escapeHtml(row?.captain || '—')}</span>
        <span>Members: ${escapeHtml(fmt(row?.size || 0))}</span>
        <span>Recruiting: ${escapeHtml(row?.recruiting ? 'Open' : 'Closed')}</span>
        <span>Bonus: ${escapeHtml(row?.bonus_label || '—')}</span>
      </div>
    </div>
  `).join('');
}

function wireTeamFilterButtons() {
  document.querySelectorAll('.mini-filter-btn[data-team-filter]').forEach((btn) => {
    btn.addEventListener('click', () => {
      teamLeaderboardFilter = btn.dataset.teamFilter || 'season';
      document.querySelectorAll('.mini-filter-btn[data-team-filter]').forEach((candidate) => {
        candidate.classList.toggle('mini-filter-btn--active', candidate.dataset.teamFilter === teamLeaderboardFilter);
      });
      refresh();
    });
  });
}

function buildAnalyticsGroupsMarkup(data) {
  const analytics = data?.analytics || {};
  const groups = analytics?.groups || {};
  const seasonLabel = analytics?.season_label || 'Season';
  const allSeasonsLabel = analytics?.all_seasons_label || 'All Seasons';
  const hasPriorSeasons = Boolean(analytics?.has_prior_seasons);

  const groupOrder = ['race_br_combined', 'tilt', 'race_only', 'br_only', 'mycycle'];
  const metricMap = {
    race_br_combined: [
      ['Races', 'race_events'], ['Points', 'points'], ['Wins', 'wins'], ['Win Rate %', 'win_rate'], ['Unique Racers', 'unique_racers'],
      ['High Score', 'high_score'], ['PPR', 'ppr'], ['Top PPR Racer', 'top_ppr_name'], ['Top PPR', 'top_ppr'], ['Top PPR Races', 'top_ppr_events'],
    ],
    tilt: [
      ['Participants', 'participants'], ['Tilt Points', 'points'], ['Tilt Levels', 'levels'], ['Top Tiltee Finishes', 'top_tiltee'],
      ['Recorded Deaths', 'deaths'], ['Known Outcomes', 'known_outcomes'], ['Survival Rate %', 'survival_rate'], ['PPR', 'ppr'],
    ],
    race_only: [
      ['Race Count', 'race_events'], ['Race Points', 'points'], ['Race Wins', 'wins'], ['Win Rate %', 'win_rate'], ['Unique Racers', 'unique_racers'],
      ['Race High Score', 'high_score'], ['Race PPR', 'ppr'], ['Top PPR Racer', 'top_ppr_name'], ['Top PPR', 'top_ppr'], ['Top PPR Races', 'top_ppr_events'],
    ],
    br_only: [
      ['BR Races', 'race_events'], ['BR Points', 'points'], ['BR Wins', 'wins'], ['Win Rate %', 'win_rate'], ['Unique Racers', 'unique_racers'],
      ['BR High Score', 'high_score'], ['BR PPR', 'ppr'], ['Top PPR Racer', 'top_ppr_name'], ['Top PPR', 'top_ppr'], ['Top PPR Races', 'top_ppr_events'],
    ],
    mycycle: [
      ['Tracked Racers', 'tracked_racers'], ['Cycles Completed', 'cycles_completed'], ['Near Complete', 'near_complete'], ['Current Cycle Races', 'current_cycle_races'],
    ],
  };

  const renderedGroups = groupOrder.map((groupKey) => {
    const group = groups[groupKey];
    if (!group) return '';
    const seasonStats = group?.season || {};
    const allSeasonStats = group?.all_seasons || {};
    const metrics = metricMap[groupKey] || [];

    const statsMarkup = metrics.map(([label, key]) => {
      const seasonValue = seasonStats?.[key];
      const allValue = hasPriorSeasons ? allSeasonStats?.[key] : null;
      const normalizedSeason = (typeof seasonValue === 'number') ? fmt(seasonValue) : (seasonValue || '—');
      const normalizedAll = hasPriorSeasons
        ? ((typeof allValue === 'number') ? fmt(allValue) : (allValue || '—'))
        : 'N/A';

      return `<div class="analytics-stat">
        <div class="analytics-stat__label">${escapeHtml(label)}</div>
        <div class="analytics-stat__compare">
          <span><strong>${escapeHtml(seasonLabel)}:</strong> ${escapeHtml(String(normalizedSeason))}</span>
          <span><strong>${escapeHtml(allSeasonsLabel)}:</strong> ${escapeHtml(String(normalizedAll))}</span>
        </div>
      </div>`;
    }).join('');

    return `<section class="analytics-group">
      <h3 class="analytics-group__title">${escapeHtml(group?.title || groupKey)}</h3>
      <div class="analytics-grid">${statsMarkup}</div>
    </section>`;
  }).filter(Boolean);

  const metricCount = renderedGroups.length
    ? groupOrder.reduce((sum, key) => sum + ((metricMap[key] || []).length), 0)
    : 0;
  const analyticsLabel = hasPriorSeasons
    ? `Season vs All Seasons • ${metricCount} metrics`
    : `Current Season Only • ${metricCount} metrics`;

  if (!renderedGroups.length) {
    return {
      markup: '<section class="analytics-group"><h3 class="analytics-group__title">Analytics Snapshot</h3><div class="empty">No analytics available yet.</div></section>',
      label: analyticsLabel,
    };
  }

  return { markup: renderedGroups.join(''), label: analyticsLabel };
}



const trendControls = { range: '21', from: '', to: '', grouping: 'daily', metric: 'total_races', compare: false };
let latestTrendPayload = null;
let trendExportRows = [];
const TREND_DAY_MS = 86400000;

function trendDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(value || ''))) return null;
  const stamp = Date.parse(`${value}T00:00:00Z`);
  return Number.isFinite(stamp) && new Date(stamp).toISOString().slice(0, 10) === value ? stamp : null;
}

function groupTrendRows(rows, grouping, shiftDays = 0) {
  const groups = new Map();
  rows.forEach(row => {
    const stamp = trendDate(row.date);
    if (stamp === null) return;
    const date = new Date(stamp + shiftDays * TREND_DAY_MS);
    if (grouping === 'weekly') date.setUTCDate(date.getUTCDate() - (date.getUTCDay() + 6) % 7);
    const key = date.toISOString().slice(0, 10);
    if (!groups.has(key)) groups.set(key, { date: key, days: 0, unique_racers: 0, unique_participants: 0, total_races: 0, race_count: 0, br_count: 0, total_points: 0 });
    const bucket = groups.get(key);
    bucket.days++;
    ['unique_racers', 'unique_participants', 'total_races', 'race_count', 'br_count'].forEach(field => bucket[field] += Number(row[field]) || 0);
    bucket.total_points += Number.isFinite(Number(row.total_points)) && row.total_points != null
      ? Number(row.total_points) : (Number(row.ppr) || 0) * (Number(row.total_races) || 0);
  });
  return [...groups.values()].sort((a, b) => a.date.localeCompare(b.date)).map(row => ({ ...row,
    unique_racers: row.unique_racers / row.days,
    unique_participants: row.unique_participants / row.days,
    ppr: row.total_races ? row.total_points / row.total_races : 0,
  }));
}

function selectTrendWindow(rows, controls = trendControls) {
  const sorted = rows.filter(row => trendDate(row.date) !== null).slice().sort((a, b) => a.date.localeCompare(b.date));
  if (!sorted.length) return { rows: [], previous: [], label: 'No trend data yet.' };
  const latest = trendDate(sorted[sorted.length - 1].date);
  const earliest = trendDate(sorted[0].date);
  let start = earliest, end = latest;
  if (controls.range === 'custom') {
    start = controls.from ? trendDate(controls.from) : earliest;
    end = controls.to ? trendDate(controls.to) : latest;
    if (start === null || end === null || start > end) return { rows: [], previous: [], label: 'Choose a valid start and end date.' };
  } else if (controls.range !== 'all') {
    start = latest - (Number(controls.range) - 1) * TREND_DAY_MS;
  }
  const days = Math.round((end - start) / TREND_DAY_MS) + 1;
  const current = sorted.filter(row => trendDate(row.date) >= start && trendDate(row.date) <= end);
  const previous = controls.compare ? sorted.filter(row => trendDate(row.date) >= start - days * TREND_DAY_MS && trendDate(row.date) < start) : [];
  return {
    rows: groupTrendRows(current, controls.grouping),
    previous: groupTrendRows(previous, controls.grouping, days),
    previousOriginal: groupTrendRows(previous, controls.grouping),
    label: `${new Date(start).toISOString().slice(0, 10)} through ${new Date(end).toISOString().slice(0, 10)}${controls.compare ? ' · Previous period aligned to current dates' : ''}`,
  };
}

function exportTrendCsv() {
  if (!trendExportRows.length) return;
  const fields = ['period', 'date', 'unique_participants', 'unique_racers', 'race_count', 'br_count', 'total_races', 'total_points', 'ppr'];
  const lines = [fields.join(','), ...trendExportRows.map(row => fields.map(field => JSON.stringify(row[field] ?? '')).join(','))];
  const url = URL.createObjectURL(new Blob([lines.join('\r\n')], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a'); link.href = url; link.download = 'mystats-trends.csv'; link.click();
  URL.revokeObjectURL(url);
}

function wireTrendControls() {
  ['range', 'from', 'to', 'grouping', 'metric', 'compare'].forEach(key => {
    const input = el(`trend-${key}`);
    input.addEventListener('change', () => {
      trendControls[key] = key === 'compare' ? input.checked : input.value;
      el('trend-custom-dates').hidden = trendControls.range !== 'custom';
      if (latestTrendPayload) { renderRaceTrends(latestTrendPayload); enhanceDashboard(latestTrendPayload); }
    });
  });
  el('trend-export').addEventListener('click', exportTrendCsv);
}

const trendChartInstances = [];
const pendingTrendCharts = [];

function mountTrendCharts() {
  pendingTrendCharts.forEach(({ id, title, rows, valueKey, labelKey, formatter }) => {
    const canvas = document.getElementById(id);
    if (!canvas || typeof Chart === 'undefined') return;
    trendChartInstances.push(new Chart(canvas, {
      type: 'line',
      data: {
        labels: rows.map(row => String(row?.[labelKey] || '—')),
        datasets: [{ label: title, data: rows.map(row => {
          const value = Number(row?.[valueKey] || 0);
          return !row.currentMissing && Number.isFinite(value) ? value : null;
        }), borderColor: '#58d8e8', backgroundColor: 'rgba(88,216,232,0.12)',
        fill: true, pointRadius: 3, tension: 0.15 }, ...(rows.some(row => row.comparisonValue != null) ? [{
          label: 'Previous period (aligned)', data: rows.map(row => row.comparisonValue ?? null),
          borderColor: '#ffbf69', borderDash: [6, 4], pointRadius: 2, fill: false,
        }] : [])],
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        interaction: { mode: 'index', intersect: false },
        plugins: { legend: { display: rows.some(row => row.comparisonValue != null), labels: { color: '#b8c5d8' } }, tooltip: {
          callbacks: { label: context => `${context.dataset.label}: ${formatter(context.parsed.y)}` },
        } },
        scales: {
          x: { ticks: { color: '#b8c5d8', maxTicksLimit: 7 }, grid: { color: 'rgba(180,200,220,0.08)' } },
          y: { beginAtZero: true, ticks: { color: '#b8c5d8' }, grid: { color: 'rgba(180,200,220,0.08)' } },
        },
      },
    }));
  });
}

function renderSimpleLineChart(title, rows, valueKey, labelKey, formatter = (v) => fmt(v)) {
  if (!Array.isArray(rows) || !rows.length) {
    return `<section class="analytics-group"><h3 class="analytics-group__title">${escapeHtml(title)}</h3><div class="empty">No trend data yet.</div></section>`;
  }

  if (typeof Chart !== 'undefined') {
    const id = `trend-chart-${pendingTrendCharts.length}`;
    pendingTrendCharts.push({ id, title, rows, valueKey, labelKey, formatter });
    const summary = rows.map(row => `${escapeHtml(String(row?.[labelKey] || '—'))}: <strong>${row.currentMissing ? 'No record' : escapeHtml(String(formatter(Number(row?.[valueKey] || 0))))}</strong>${row.comparisonValue != null ? ` (previous: ${escapeHtml(String(formatter(row.comparisonValue)))})` : ''}`).join(' · ');
    return `<section class="analytics-group trend-chart-card"><h3 class="analytics-group__title">${escapeHtml(title)}</h3>
      <div style="position:relative;height:240px"><canvas id="${id}" role="img" aria-label="${escapeHtml(title)}"></canvas></div>
      <div class="trend-line-summary">${summary}</div></section>`;
  }

  const chartWidth = 560;
  const chartHeight = 180;
  const padX = 22;
  const padY = 16;
  const innerW = chartWidth - (padX * 2);
  const innerH = chartHeight - (padY * 2);

  const values = rows.map((row) => Number(row?.[valueKey] || 0));
  const labels = rows.map((row) => String(row?.[labelKey] || '—'));
  const maxValue = Math.max(...values, 1);
  const minValue = Math.min(...values, 0);
  const range = Math.max(1, maxValue - minValue);

  const points = values.map((value, idx) => {
    const x = padX + ((innerW * idx) / Math.max(1, values.length - 1));
    const y = padY + (innerH - (((value - minValue) / range) * innerH));
    return { x, y, value, label: labels[idx] };
  });

  const pathD = points.map((pt, idx) => `${idx === 0 ? 'M' : 'L'}${pt.x.toFixed(2)} ${pt.y.toFixed(2)}`).join(' ');

  const dots = points.map((pt) => (
    `<circle data-history-day="${/^\d{4}-\d{2}-\d{2}$/.test(pt.label) ? escapeHtml(pt.label) : ''}" class="trend-line-dot" cx="${pt.x.toFixed(2)}" cy="${pt.y.toFixed(2)}" r="3.5">
      <title>${escapeHtml(`${pt.label}: ${formatter(pt.value)}`)}</title>
    </circle>`
  )).join('');

  const xTicks = points.map((pt, idx) => {
    if (points.length > 8 && idx % 2 !== 0) return '';
    return `<text class="trend-axis-label" x="${pt.x.toFixed(2)}" y="${(chartHeight - 2).toFixed(2)}" text-anchor="middle">${escapeHtml(pt.label)}</text>`;
  }).join('');

  const summary = rows.map((row) => {
    const label = String(row?.[labelKey] || '—');
    const value = Number(row?.[valueKey] || 0);
    return `<span>${escapeHtml(label)}: <strong>${escapeHtml(formatter(value))}</strong></span>`;
  }).join('');

  return `<section class="analytics-group trend-chart-card"><h3 class="analytics-group__title">${escapeHtml(title)}</h3>
    <svg class="trend-line-chart" viewBox="0 0 ${chartWidth} ${chartHeight}" role="img" aria-label="${escapeHtml(title)}">
      <line x1="${padX}" y1="${chartHeight - padY}" x2="${chartWidth - padX}" y2="${chartHeight - padY}" class="trend-axis"></line>
      <line x1="${padX}" y1="${padY}" x2="${padX}" y2="${chartHeight - padY}" class="trend-axis"></line>
      <path d="${pathD}" class="trend-line-path"></path>
      ${dots}
      ${xTicks}
    </svg>
    <div class="trend-line-summary">${summary}</div>
  </section>`;
}

function renderRaceTrends(data) {
  latestTrendPayload = data;
  const trends = data?.race_trends || {};
  const summary = trends?.summary || {};
  const seasonSeries = Array.isArray(trends?.season_series) ? trends.season_series : [];
  const dailyRows = Array.isArray(trends?.daily_current_season) ? trends.daily_current_season : [];

  const summaryHost = el('trends-summary');
  const chartHost = el('trend-charts');
  if (!chartHost) return;

  if (summaryHost) summaryHost.innerHTML = [
    { label: 'Avg Unique Racers / Day', value: fmt(summary.avg_racers_per_day || 0) },
    { label: 'Avg Races / Day', value: fmt(summary.avg_races_per_day || 0) },
    { label: 'Avg PPR / Day', value: fmt(summary.avg_ppr_per_day || 0) },
    { label: 'Rolling 7D Racers', value: fmt(summary.rolling7_avg_racers || 0) },
    { label: 'Rolling 7D Races', value: fmt(summary.rolling7_avg_races || 0) },
    { label: 'Race Share %', value: fmt(summary.race_share_percent || 0) },
    { label: 'BR Share %', value: fmt(summary.br_share_percent || 0) },
    { label: 'Days with Data', value: fmt(summary.days_with_data || 0) },
  ].map((kpi) => `<div class="kpi"><div class="kpi-label">${escapeHtml(kpi.label)}</div><div class="kpi-value">${escapeHtml(String(kpi.value))}</div></div>`).join('');

  const windowed = selectTrendWindow(dailyRows);
  const latestDays = windowed.rows;
  const previousByDate = new Map(windowed.previous.map(row => [row.date, row]));
  trendExportRows = [...latestDays.map(row => ({ ...row, period: 'current' })),
    ...(windowed.previousOriginal || []).map(row => ({ ...row, period: 'previous' }))];
  const status = el('trend-status');
  if (status) status.textContent = `${windowed.label}${trendControls.grouping === 'weekly' ? ' · Week labels are Mondays; partial weeks use selected days. Winners = average daily count on recorded days; PPR is weighted by event count.' : ''}${trendControls.compare && !windowed.previous.length ? ' · No data in previous period.' : ''}`;
  const exportButton = el('trend-export');
  if (exportButton) exportButton.disabled = !trendExportRows.length;
  const chart = (title, rows, key, label, formatter = value => fmt(value), compare = false) => {
    const annotated = compare ? rows.map(row => ({ ...row, comparisonValue: previousByDate.get(row.date)?.[key] ?? null })) : rows.slice();
    if (compare && trendControls.compare && typeof Chart !== 'undefined') {
      const currentDates = new Set(rows.map(row => row.date));
      windowed.previous.forEach(row => {
        if (!currentDates.has(row.date)) annotated.push({ date: row.date, currentMissing: true, comparisonValue: row[key] });
      });
      annotated.sort((a, b) => a.date.localeCompare(b.date));
    }
    let markup = renderSimpleLineChart(title, annotated, key, label, formatter);
    if (compare && trendControls.compare && typeof Chart === 'undefined' && windowed.previous.length) {
      markup += renderSimpleLineChart(`${title} — Previous period (aligned)`, windowed.previous, key, label, formatter);
    }
    return markup;
  };
  const analyticsSection = buildAnalyticsGroupsMarkup(data);

  pendingTrendCharts.length = 0;
  const metric = trendControls.metric;
  const include = key => metric === 'all' || metric === key;
  const charts = [`<details><summary>Season and all-season statistics</summary>${analyticsSection.markup}</details>`];
  if (include('unique_participants')) charts.push(chart(trendControls.grouping === 'weekly' ? 'Weekly Average Daily Participants' : 'Daily Unique Participants', latestDays, 'unique_participants', 'date', v => Number(v).toLocaleString(undefined,{maximumFractionDigits:1}), true));
  if (include('unique_racers')) charts.push(chart('Unique Winners per Season', seasonSeries, 'unique_racers', 'season_label'));
  if (include('total_races')) charts.push(chart('Total Races per Season', seasonSeries, 'total_races', 'season_label'));
  if (metric === 'ppr') charts.push(chart('Winning Points per Event per Season', seasonSeries, 'ppr', 'season_label', v => Number(v).toFixed(2)));
  if (metric === 'br_count') charts.push(chart('BR per Season', seasonSeries, 'br_count', 'season_label'));
  if (include('unique_racers')) charts.push(chart(trendControls.grouping === 'weekly' ? 'Weekly Average Daily Winners' : 'Daily Unique Winners', latestDays, 'unique_racers', 'date', v => Number(v).toLocaleString(undefined, { maximumFractionDigits: 1 }), true));
  if (include('total_races')) charts.push(chart('Race + BR Events', latestDays, 'total_races', 'date', undefined, true));
  if (include('ppr')) charts.push(chart('Winning Points per Race + BR Event', latestDays, 'ppr', 'date', v => Number(v).toFixed(2), true));
  if (include('br_count')) charts.push(chart('BR Events', latestDays, 'br_count', 'date', undefined, true));

  chartHost.classList.add('trend-grid');
  trendChartInstances.splice(0).forEach(chart => chart.destroy());
  chartHost.innerHTML = charts.join('');
  mountTrendCharts();
  const trendLabel = trends.has_prior_seasons
    ? `Season + historical trends • ${seasonSeries.length} seasons`
    : 'Current season trends only';
  el('trends-range-pill').textContent = `${trendLabel} • ${analyticsSection.label}`;
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


function wireSeasonControls() {
  const queryInput = el('season-query');
  const sortBySelect = el('season-sort-by');
  const sortOrderSelect = el('season-sort-order');
  if (queryInput) {
    queryInput.value = seasonQuery;
    queryInput.addEventListener('input', () => {
      seasonQuery = String(queryInput.value || '').trim();
      seasonPage = 1;
      refresh();
    });
  }
  if (sortBySelect) {
    sortBySelect.value = seasonSortBy;
    sortBySelect.addEventListener('change', () => {
      seasonSortBy = sortBySelect.value || 'completed';
      seasonPage = 1;
      refresh();
    });
  }
  if (sortOrderSelect) {
    sortOrderSelect.value = seasonSortOrder;
    sortOrderSelect.addEventListener('change', () => {
      seasonSortOrder = sortOrderSelect.value === 'asc' ? 'asc' : 'desc';
      seasonPage = 1;
      refresh();
    });
  }
}

function wireSeasonPaginationControls(pageInfo) {
  const prevBtn = el('season-prev-page');
  const nextBtn = el('season-next-page');
  const pageLabel = el('season-page-info');
  if (pageLabel) {
    pageLabel.textContent = pageInfo ? `Page ${pageInfo.page}/${Math.max(1, pageInfo.total_pages || 1)}` : 'Page 1/1';
  }
  if (prevBtn) {
    prevBtn.disabled = !pageInfo || pageInfo.page <= 1;
    prevBtn.onclick = () => {
      seasonPage = Math.max(1, seasonPage - 1);
      refresh();
    };
  }
  if (nextBtn) {
    nextBtn.disabled = !pageInfo || pageInfo.page >= (pageInfo.total_pages || 1);
    nextBtn.onclick = () => {
      seasonPage = Math.min(pageInfo.total_pages || seasonPage, seasonPage + 1);
      refresh();
    };
  }
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




let guideLoaded = false;

async function loadGuideContent() {
  if (guideLoaded) return;
  const host = el('guide-content');
  if (!host) return;
  try {
    const resp = await fetch('/dashboard/readme', { cache: 'no-store' });
    if (!resp.ok) throw new Error(`Guide unavailable (${resp.status})`);
    const htmlText = await resp.text();
    const parsed = new DOMParser().parseFromString(htmlText, 'text/html');
    const bodyHtml = parsed.body ? parsed.body.innerHTML : htmlText;
    host.innerHTML = bodyHtml;
    guideLoaded = true;
  } catch (error) {
    host.innerHTML = `<div class="empty">${escapeHtml(t('Unable to load MyStats data.'))}</div>`;
  }
}

function getRequestedViewFromLocation() {
  const hashView = String(window.location.hash || '').replace('#', '').trim();
  const validViews = new Set(['mycycle', 'season-quests', 'tilt', 'rivals', 'races', 'teams', 'trends', 'guide', 'overlays']);
  if (validViews.has(hashView)) return hashView;

  const viewFromQuery = new URLSearchParams(window.location.search).get('view');
  return validViews.has(viewFromQuery) ? viewFromQuery : null;
}

function setActiveView(viewName) {
  activeView = viewName;
  if (viewName === 'overlays' && el('preset-size')) el('preset-size').onchange();
  if (dashboardLastPayload) setTimeout(() => renderDashboardPayload(dashboardLastPayload, false), 0);
  if (window.location.hash !== `#${activeView}`) {
    window.history.replaceState(null, '', `#${activeView}`);
  }

  document.querySelectorAll('.dashboard-nav-btn[data-view]').forEach((btn) => {
    const isActive = btn.dataset.view === activeView;
    btn.classList.toggle('dashboard-nav-btn--active', isActive);
    btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
  });

  document.querySelectorAll('[data-panel]').forEach((panel) => {
    const hidden = panel.dataset.panel !== activeView;
    panel.classList.toggle('is-hidden', hidden);
    panel.setAttribute('aria-hidden', hidden ? 'true' : 'false');
  });
}

function wireViewTabs() {
  const tabs = Array.from(document.querySelectorAll('.dashboard-nav-btn[data-view]'));
  tabs.forEach((btn, index) => {
    btn.addEventListener('click', () => setActiveView(btn.dataset.view));
    btn.addEventListener('keydown', (event) => {
      if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return;
      event.preventDefault();
      const delta = event.key === 'ArrowRight' ? 1 : -1;
      const nextIndex = (index + delta + tabs.length) % tabs.length;
      tabs[nextIndex].focus();
      setActiveView(tabs[nextIndex].dataset.view);
    });
  });
}

function buildRefreshParams() {
  const params = new URLSearchParams({
    mycycle_page: String(mycyclePage),
    mycycle_page_size: String(mycyclePageSize),
  });
  if (mycycleQuery) params.set('mycycle_query', mycycleQuery);
  if (seasonQuery) params.set('season_query', seasonQuery);
  params.set('season_page', String(seasonPage));
  params.set('session', el('cycle-session')?.value || '');
  params.set('cycle_sort', el('cycle-sort')?.value || 'leaderboard');
  params.set('tilt_scope', el('tilt-scope')?.value || 'season');
  params.set('season_page_size', String(seasonPageSize));
  params.set('season_sort_by', seasonSortBy);
  params.set('season_sort_order', seasonSortOrder);
  return params;
}

function renderDashboardPayload(data, received = true) {
  const panel = document.querySelector(`[data-panel="${activeView}"]`);
  const detailKey = node => `${node.closest(".row")?.querySelector("[data-player]")?.dataset.player || node.closest(".row")?.querySelector("strong")?.textContent || "panel"}|${node.querySelector("summary")?.textContent}`;
  const openDetails = new Set([...panel?.querySelectorAll("details[open]") || []].map(detailKey));
  dashboardLastPayload = data;
  if (received) { dashboardLastReceived = Date.now(); setConnectionStatus('Connected · live updates'); }
  currentLanguage = data?.settings?.language || currentLanguage || 'en';
  el('updated-at').textContent = data.updated_at ? `${t('Updated')} ${data.updated_at}` : t('Updated now');
  const renderers = {'mycycle': renderMyCycleRows, 'season-quests': renderSeasonQuestRows,
    tilt: renderTiltRows, rivals: renderRivalsRows, races: renderRaceDashboardRows,
    teams: renderTeamsRows, trends: renderRaceTrends};
  const focused = document.activeElement;
  const draft = focused?.id ? {id: focused.id, value: focused.value, start: focused.selectionStart, end: focused.selectionEnd} : null;
  renderers[activeView]?.(data);
  if (draft) {
    const input = el(draft.id);
    if (input && input !== focused) { input.value = draft.value; input.focus(); try { input.setSelectionRange(draft.start, draft.end); } catch (_) {} }
  }
  enhanceDashboard(data);
  panel?.querySelectorAll("details").forEach(node => { if (openDetails.has(detailKey(node))) node.open = true; });
}

function renderDashboardError(error) {
  console.error('dashboard refresh failed', error);
  setConnectionStatus('Reconnecting — showing last successful data', true);
  if (dashboardLastPayload) return;
  const fallback = `<div class="empty">${escapeHtml(t('Unable to load MyStats data.'))}</div>`;
  ['mycycle', 'season-quests', 'tilt-leaderboard', 'rivals-leaderboard', 'races-leaderboard', 'teams-leaderboard', 'trend-charts'].forEach((id) => {
    const node = el(id);
    if (node) node.innerHTML = fallback;
  });
}

async function refresh() {
  try {
    const params = buildRefreshParams();
    const nextQuery = params.toString();
    if (dashboardStream && dashboardStreamQuery && dashboardStreamQuery !== nextQuery) {
      startDashboardStream();
    }
    const resp = await fetch(`/api/dashboard/main?${nextQuery}`, { cache: 'no-store' });
    if (!resp.ok) throw new Error(`Dashboard request failed (${resp.status})`);
    const data = await resp.json();
    if (nextQuery === buildRefreshParams().toString()) renderDashboardPayload(data);
  } catch (error) {
    renderDashboardError(error);
  }
}

function stopDashboardStream() {
  if (dashboardStream) {
    dashboardStream.close();
    dashboardStream = null;
    dashboardStreamQuery = '';
  }
  if (dashboardStreamReconnectTimer) {
    clearTimeout(dashboardStreamReconnectTimer);
    dashboardStreamReconnectTimer = null;
  }
}

function startDashboardStream() {
  stopDashboardStream();
  if (typeof window === 'undefined' || !('EventSource' in window)) return false;

  const params = buildRefreshParams();
  dashboardStreamQuery = params.toString();
  const streamUrl = `/api/dashboard/main/stream?${dashboardStreamQuery}`;
  const stream = new EventSource(streamUrl);
  dashboardStream = stream;

  stream.addEventListener('update', (event) => {
    try {
      const data = JSON.parse(event.data || '{}');
      if (dashboardStream === stream) renderDashboardPayload(data);
    } catch (error) {
      console.error('dashboard stream parse failed', error);
    }
  });

  stream.onerror = () => {
    setConnectionStatus('Reconnecting — showing last successful data', true);
    stopDashboardStream();
    dashboardStreamReconnectTimer = setTimeout(() => {
      refresh();
      startDashboardStream();
    }, 5000);
  };

  return true;
}

// Dashboard controls and details use the same read-only data as the desktop tools.
let dashboardLastPayload = null;
let dashboardLastReceived = 0;
let detailRequest = 0;
const dashboardFilters = {};
function readPreference(key, fallback) {
  try { return JSON.parse(localStorage.getItem(`mystats.${key}`)) ?? fallback; } catch (_) { return fallback; }
}
function savePreference(key, value) {
  try { localStorage.setItem(`mystats.${key}`, JSON.stringify(value)); } catch (_) { /* Private browser storage may be unavailable. */ }
}
function setConnectionStatus(message, warning = false) {
  const status = el('connection-status');
  if (status) { status.textContent = message; status.classList.toggle('status-warning', warning); }
}
function playerButton(row) {
  return `<button class="player-link" data-player="${escapeHtml(row.username || row.player || '')}">${escapeHtml(row.display_name || row.display || row.username || row.player || 'Unknown')}</button>`;
}
function metric(label, value) { return `<span><small>${escapeHtml(label)}</small><strong>${escapeHtml(value ?? 'Unavailable')}</strong></span>`; }
function progressLine(label, value, target) {
  const n = Number(value || 0), goal = Number(target || 0);
  if (goal <= 0) return '';
  return `<div class="quest-progress"><span>${escapeHtml(label)}: ${fmt(n)} / ${fmt(goal)}</span><progress max="${goal}" value="${Math.min(goal, n)}" aria-label="${escapeHtml(label)}"></progress></div>`;
}
function installDashboardControls() {
  const nav = document.querySelector('.dashboard-nav');
  nav.insertAdjacentHTML('beforeend', '<button class="dashboard-nav-btn" data-view="overlays" role="tab" aria-selected="false" aria-controls="panel-overlays">OBS presets</button>');
  document.querySelector('.topbar').insertAdjacentHTML('beforeend', '<label>Theme <select id="dashboard-theme"><option value="midnight">Midnight</option><option value="darkly">Darkly</option></select></label>');
  document.querySelector('.topbar').insertAdjacentHTML('afterend', '<div id="connection-status" class="connection-status" role="status" aria-live="polite">Connecting…</div>');
  const theme = el('dashboard-theme'); theme.value = readPreference('theme', 'darkly');
  document.documentElement.dataset.theme = theme.value;
  theme.onchange = () => { document.documentElement.dataset.theme = theme.value; savePreference('theme', theme.value); };
  const definitions = [
    ['mycycle','MyCycle session','<label>Session <select id="cycle-session"></select></label><label>Order <select id="cycle-sort"><option value="leaderboard">Cycles completed</option><option value="closest">Closest to completion</option></select></label>'],
    ['tilt','Tilt scope','<label>Scope <select id="tilt-scope"><option value="season">Season</option><option value="today">Today</option><option value="current">Current run</option></select></label>'],
    ['races','Season Race / BR','<label>Metric <select id="race-metric"><option value="points">Points</option><option value="events">Entries</option><option value="high">High score</option><option value="kills">BR kills</option><option value="damage">BR damage</option><option value="survival">BR survival average</option></select></label>'],
    ['teams','Team window','<label>Order <select id="teams-sort"><option value="points">Points</option><option value="name">Name</option><option value="size">Members</option></select></label><label><input id="teams-recruiting" type="checkbox"> Recruiting only</label>'],
    ['season-quests','Season quests','']
  ];
  for (const [view, scope, extra] of definitions) {
    const host = el(`panel-${view}`).querySelector('.leaderboard-panel');
    const controls = document.createElement('div'); controls.className = 'shared-controls';
    controls.innerHTML = `<span class="scope-label">${scope}</span>${extra}<label>Find <input type="search" data-find="${view}" placeholder="Player or team"></label><button data-reset="${view}">Reset</button><label><input type="checkbox" data-compact="${view}" checked> Compact list</label>`;
    host.prepend(controls);
  }
  document.querySelectorAll('[data-find]').forEach(input => {
    let pending; input.oninput = () => {
      const view = input.dataset.find;
      if (view === 'mycycle' || view === 'season-quests') { clearTimeout(pending); pending = setTimeout(() => { if (view === 'mycycle') { mycycleQuery = input.value.trim(); mycyclePage = 1; } else { seasonQuery = input.value.trim(); seasonPage = 1; } refresh(); }, 250); }
      else { dashboardFilters[view] = input.value.toLowerCase(); if (dashboardLastPayload) enhanceDashboard(dashboardLastPayload); }
    };
  });
  document.querySelectorAll('[data-compact]').forEach(input => input.onchange = () => { const panel = el(`panel-${input.dataset.compact}`); panel.classList.toggle('expanded-list', !input.checked); panel.querySelectorAll('.row details').forEach(details => details.open = !input.checked); });
  document.querySelectorAll('[data-reset]').forEach(button => button.onclick = () => {
    const view = button.dataset.reset; dashboardFilters[view] = '';
    document.querySelector(`[data-find="${view}"]`).value = '';
    if (view === 'mycycle') { mycyclePage = 1; mycycleQuery = ''; el('cycle-sort').value = 'leaderboard'; }
    if (view === 'season-quests') { seasonPage = 1; seasonQuery = ''; el('season-query').value = ''; seasonSortBy = 'completed'; seasonSortOrder = 'desc'; el('season-sort-by').value = 'completed'; el('season-sort-order').value = 'desc'; }
    if (view === 'tilt') { el('tilt-scope').value = 'season'; tiltSortBy = 'tilt_points'; el('tilt-sort-by').value = 'tilt_points'; }
    if (view === 'races') { raceDashboardFilter = 'both'; el('race-metric').value = 'points'; }
    if (view === 'teams') { el('teams-sort').value = 'points'; el('teams-recruiting').checked = false; teamLeaderboardFilter = 'season'; }
    document.querySelectorAll('[data-race-filter]').forEach(btn => btn.classList.toggle('mini-filter-btn--active', btn.dataset.raceFilter === raceDashboardFilter));
    document.querySelectorAll('[data-team-filter]').forEach(btn => btn.classList.toggle('mini-filter-btn--active', btn.dataset.teamFilter === teamLeaderboardFilter));
    refresh();
  });
  ['cycle-session','cycle-sort','tilt-scope'].forEach(id => el(id).onchange = () => { mycyclePage = 1; refresh(); startDashboardStream(); });
  ['race-metric','teams-recruiting','teams-sort'].forEach(id => el(id).onchange = () => dashboardLastPayload && enhanceDashboard(dashboardLastPayload));
  el('rivals-export').insertAdjacentHTML('afterend','<button id="rivals-reset">Reset</button>');
  el('rivals-reset').onclick = () => { rivalsSearchQuery = ''; rivalsSortBy = 'closest'; rivalsGapPreset = 'all'; el('rivals-search').value = ''; el('rivals-sort').value = 'closest'; el('rivals-preset').value = 'all'; savePreference('pinnedRival',''); refresh(); };
  el('trend-export').insertAdjacentHTML('afterend','<button id="trends-reset" class="mini-filter-btn">Reset</button>');
  el('trends-reset').onclick = () => { Object.assign(trendControls,{range:'21',from:'',to:'',grouping:'daily',metric:'total_races',compare:false}); for (const key of ['range','from','to','grouping','metric']) el(`trend-${key}`).value = trendControls[key]; el('trend-compare').checked = false; el('trend-custom-dates').hidden = true; if (dashboardLastPayload) renderDashboardPayload(dashboardLastPayload,false); };
  document.body.insertAdjacentHTML('beforeend', '<dialog id="player-drawer" aria-labelledby="drawer-title"><button id="drawer-close" class="drawer-close" aria-label="Close details">Close</button><h2 id="drawer-title">Player details</h2><div id="drawer-content"></div></dialog>');
  el('drawer-close').onclick = () => { detailRequest++; el('player-drawer').close(); };
  document.addEventListener('click', event => {
    const player = event.target.closest('[data-player]');
    if (player) openPlayerDetails(player.dataset.player);
    const day = event.target.closest('[data-history-day]');
    if (day) openPlayerDetails('', day.dataset.historyDay);
  });
  document.querySelector('main').insertAdjacentHTML('beforeend', '<section id="panel-overlays" class="guide-shell is-hidden" data-panel="overlays" role="tabpanel"><h2>OBS presentation presets</h2><div id="overlay-presets"></div></section>');
  installOverlayPresets();
  installGuide();
  setInterval(() => {
    if (dashboardLastReceived && Date.now() - dashboardLastReceived > 90000) setConnectionStatus('Data is stale — reconnecting; last successful results retained', true);
    document.querySelectorAll('[data-bonus-end]').forEach(node => {
      const seconds = Math.max(0, Math.ceil((Date.parse(node.dataset.bonusEnd) - Date.now()) / 1000));
      node.textContent = Number.isFinite(seconds) ? (seconds ? `Bonus ends in ${Math.floor(seconds / 60)}m ${seconds % 60}s` : 'Bonus ended') : 'Bonus timing unavailable';
    });
  }, 1000);
}
function matchesDashboardFilter(row, view) {
  const query = dashboardFilters[view] || '';
  return !query || `${row.username || ''} ${row.display_name || ''} ${row.name || ''}`.toLowerCase().includes(query);
}
function enhanceDashboard(data) {
  const view = activeView;
  if (view === 'mycycle') {
    const selector = el('cycle-session'), selected = data.mycycle?.session?.id;
    if (document.activeElement !== selector) {
      selector.innerHTML = (data.mycycle?.sessions || []).map(x => `<option value="${escapeHtml(x.id)}">${escapeHtml(x.name || x.id)}${x.active ? '' : ' (inactive)'}</option>`).join('');
      if (selected) selector.value = selected;
    }
    const rows = data.mycycle?.rows || [];
    const cards = [...el('mycycle').querySelectorAll('.row')];
    cards.forEach((card, i) => {
      const row = rows[i]; if (!row) return;
      card.hidden = !matchesDashboardFilter(row, view);
      const name = card.querySelector('.name'); if (name) name.innerHTML = playerButton(row);
      card.classList.toggle('one-away', row.missing_places?.length === 1);
      if (row.missing_places?.length === 1 && !card.querySelector('.one-away-label')) card.insertAdjacentHTML('beforeend', `<span class="one-away-label">One position away: ${escapeHtml(row.missing_places[0])}</span>`);
      if (!card.querySelector('details')) card.insertAdjacentHTML('beforeend', `<details><summary>Cycle history</summary><p>${fmt(row.cycles_completed)} completed · Last cycle: ${fmt(row.last_cycle_races)} entries · Completed ${escapeHtml(row.last_cycle_completed_at || 'not recorded')}</p>${(row.cycle_history || []).slice().reverse().map(c => `<p>${escapeHtml(c.completed_at || 'Unknown date')} · ${fmt(c.races_used)} entries (${fmt(c.race_races)} Race / ${fmt(c.br_races)} BR)</p>`).join('') || '<p>Earlier cycle history was not recorded.</p>'}<button data-player="${escapeHtml(row.username)}">Open recorded results</button></details>`);
    });
    if (data.mycycle?.pagination && !el('mycycle-meta').textContent.includes('Summary covers')) el('mycycle-meta').textContent += ' · Summary covers this page';
    // Wire empty-state pagination too, so a search can always be cleared.
    const search = el('mycycle-search');
    if (search) el('mycycle-search-btn').onclick = () => { mycycleQuery = search.value.trim(); mycyclePage = 1; refresh(); };
  }
  if (view === 'season-quests') {
    const rows = data.season_quests?.rows || [], targets = data.season_quests?.targets || {};
    [...el('season-quests').querySelectorAll('.row')].forEach((card, i) => {
      const row = rows[i]; if (!row) return; card.hidden = !matchesDashboardFilter(row, view);
      card.querySelector('.name').innerHTML = playerButton(row);
      if (card.querySelector('details')) return;
      const keys = {points:'Points',races:'Entries',race_hs:'Race high score',br_hs:'BR high score',tilt_levels:'Tilt levels',tilt_tops:'Top Tiltees',tilt_points:'Tilt points'};
      const questRow = {...row, tilt_tops:getTopTilteeCount(row)};
      const quests = Object.keys(keys).filter(key => Number(targets[key]) > 0);
      const next = quests.filter(key => Number(questRow[key] || 0) < Number(targets[key])).sort((a,b) => Number(questRow[b] || 0) / targets[b] - Number(questRow[a] || 0) / targets[a])[0];
      card.insertAdjacentHTML('beforeend', `<p class="next-goal">${next ? `Next closest: ${keys[next]} · ${fmt(targets[next] - Number(questRow[next] || 0))} remaining` : (quests.length ? 'All active quests complete' : 'No active quest targets')}</p><details><summary>Progress for each quest</summary>${quests.map(key => progressLine(keys[key],questRow[key],targets[key])).join('') || '<p>No active quest targets.</p>'}</details>`);
    });
    if (!el('season-range-pill').textContent.includes('Summary covers')) el('season-range-pill').textContent += ' · Summary covers this page';
  }
  if (view === 'tilt') {
    const rows = (data.tilt?.leaderboard || []).filter(row => matchesDashboardFilter(row,view)).map(row => ({...row, deaths:Number(row.tilt_deaths || 0), death_rate:row.known_outcomes ? row.tilt_deaths / row.known_outcomes * 100 : null})).sort((a,b) => compareTiltRows(a,b,tiltSortBy,tiltSortOrder));
    el('tilt-leaderboard').innerHTML = rows.map((row,i) => {
      const known = Number(row.known_outcomes || 0), deaths = Number(row.tilt_deaths || 0);
      return `<article class="row"><div class="row-head">${renderRankBadge(i+1)}${playerButton(row)}<span class="stat">${fmt(row.tilt_points)} pts</span></div><div class="compact-metrics">${metric('Levels',fmt(row.tilt_levels))}${metric('Top Tiltees',fmt(row.tilt_top_tiltee))}${metric('Recorded deaths', known ? fmt(deaths) : 'Unknown')}${metric('Survival',known ? `${((1-deaths/known)*100).toFixed(1)}%` : 'Unknown')}${metric('Known outcomes',`${known}/${row.tilt_levels}`)}</div></article>`;
    }).join('') || '<p class="empty">No recorded results in this scope.</p>';
    el('tilt-highlights').innerHTML = `<p class="meta">${data.tilt?.confirming_run_end ? 'Confirming run end… watching for corrected results.' : 'Watching for new results.'}</p><p>Survival uses explicit recorded outcomes only. Older exports may have unknown outcomes. Top Tiltee is a ranking, not survival.</p>`;
    // Remove speculative Pressure and Consistency choices entirely.
    [...el('tilt-sort-by').options].filter(x => ['pressure_score','consistency'].includes(x.value)).forEach(x => x.remove());
    if (!el('tilt-sort-by').value) el('tilt-sort-by').value = 'tilt_points';
  }
  if (view === 'races') {
    const choice = el('race-metric').value;
    const value = row => choice === 'survival' ? Number(row.br_survival_average || 0) : choice === 'kills' ? Number(row.br_kills || 0) : choice === 'damage' ? Number(row.br_damage || 0) : choice === 'events' ? getRaceRowTotals(row, raceDashboardFilter).events : choice === 'high' ? getRaceRowTotals(row, raceDashboardFilter).highScore : getRaceRowTotals(row, raceDashboardFilter).points;
    const rows = (data.races || []).filter(row => matchesDashboardFilter(row,view)).filter(row => raceDashboardFilter === 'both' || Number(row[`${raceDashboardFilter}_count`]) > 0).sort((a,b) => value(b)-value(a));
    el('races-leaderboard').innerHTML = rows.map((row,i) => `<article class="row"><div class="row-head">${renderRankBadge(i+1)}${playerButton(row)}<span class="stat">${fmt(value(row))} ${escapeHtml(choice)}</span></div><div class="compact-metrics">${metric('Race entries',fmt(row.race_count))}${metric('BR entries',fmt(row.br_count))}${metric('BR kills',row.br_stats_samples ? fmt(row.br_kills) : 'Unavailable')}${metric('BR damage',row.br_stats_samples ? fmt(row.br_damage) : 'Unavailable')}${metric('BR survival avg',row.br_survival_samples ? `${row.br_survival_average}s` : 'Unavailable')}</div><details><summary>More statistics</summary><p>Race high score ${fmt(row.race_hs)} · BR high score ${fmt(row.br_hs)} · BR survival: ${row.br_survival_samples ? `${Number(row.br_survival_average).toFixed(1)}s average · ${Number(row.br_survival_best).toFixed(1)}s best · ${fmt(row.br_survival_samples)} recorded rounds` : 'Unavailable in archived results'}.</p><button data-player="${escapeHtml(row.username)}">Results, records and goals</button></details></article>`).join('') || '<p class="empty">No matching players.</p>';
  }
  if (view === 'teams') {
    const rows = (data.teams?.[`top_${teamLeaderboardFilter}`] || []).filter(row => matchesDashboardFilter(row,view)).filter(row => !el('teams-recruiting').checked || row.recruiting).sort((a,b) => el('teams-sort').value === 'name' ? a.name.localeCompare(b.name) : Number(b[el('teams-sort').value] || 0) - Number(a[el('teams-sort').value] || 0));
    el('teams-leaderboard').innerHTML = rows.map((row,i) => `<article class="row"><div class="row-head">${renderRankBadge(i+1)}<strong>${escapeHtml(row.name)}</strong><span class="stat">${fmt(row.points)} pts</span></div><div class="compact-metrics">${metric('Members',row.size)}${metric('Recruiting',row.recruiting?'Open':'Closed')}${metric('Bonus',row.bonus_label)}</div>${row.bonus_end ? `<p data-bonus-end="${escapeHtml(row.bonus_end)}">Calculating bonus time…</p>` : ''}<details><summary>Roster and member results</summary><p>Team totals may include bonuses and historical membership. Member season points show individual results.</p>${(row.roster || []).map(user => { const stats = (data.races || []).find(x => x.username === user); return `<p>${playerButton(stats || {username:user})} · ${stats ? fmt(stats.total_points) + ' season points' : 'No saved race results'}</p>`; }).join('')}</details></article>`).join('') || '<p class="empty">No teams match this filter.</p>';
  }
  if (view === 'rivals' && document.activeElement?.id !== 'rival-pin') renderPinnedRival(data);
  if (view === 'trends') {
    const host = el('trend-charts');
    if (!el('trend-history-links')) host.insertAdjacentHTML('beforeend', `<details id="trend-history-links"><summary>Open recorded results by day</summary>${(data.race_trends?.daily_current_season || []).slice(-90).reverse().map(row => `<button data-history-day="${escapeHtml(row.date)}">${escapeHtml(row.date)}</button>`).join('')}</details>`);
    host.querySelectorAll('canvas').forEach(canvas => {
      if (typeof Chart === 'undefined') return;
      const chart = Chart.getChart(canvas); if (!chart) return;
      chart.options.onClick = (event, elements) => {
        if (!elements.length) return;
        const element = elements[0]; let day = String(chart.data.labels[element.index]);
        if (!/^\d{4}-\d{2}-\d{2}/.test(day)) return;
        if (element.datasetIndex === 1) {
          const windowed = selectTrendWindow(data.race_trends?.daily_current_season || []);
          const index = windowed.previous.findIndex(row => row.date === day);
          day = windowed.previousOriginal?.[index]?.date || '';
        }
        if (!day) return;
        const end = trendControls.grouping === 'weekly' ? new Date(trendDate(day) + 6 * TREND_DAY_MS).toISOString().slice(0,10) : day;
        openPlayerDetails('',day,end);
      };
    });
  }
}
async function openPlayerDetails(player, day = '', end = day) {
  const requestId = ++detailRequest, drawer = el('player-drawer');
  el('drawer-title').textContent = player ? `Player · ${player}` : `Results · ${day}${end !== day ? ` to ${end}` : ''}`;
  el('drawer-content').textContent = 'Loading recorded results…';
  if (!drawer.open) drawer.showModal();
  try {
    const response = await fetch(`/api/dashboard/details?${new URLSearchParams({player,day,end})}`);
    if (!response.ok) throw new Error('Details unavailable');
    const details = await response.json();
    if (requestId !== detailRequest) return;
    const stats = (dashboardLastPayload?.races || []).find(r => r.username === player);
    el('drawer-content').innerHTML = `${stats ? `<div class="compact-metrics">${metric('Season points',fmt(stats.total_points))}${metric('Race entries',fmt(stats.race_count))}${metric('BR entries',fmt(stats.br_count))}</div>` : ''}<p>Showing ${details.rows.length} of ${fmt(details.total)} saved results in the current season.</p><h3>Goals</h3>${details.goals.map(g => `<p>${escapeHtml(g.kind)}: ${fmt(g.progress?.[0])} / ${fmt(g.target)} points (${Number(g.progress?.[1] || 0).toFixed(1)}%)</p>`).join('') || (details.goals_error ? '<p>Saved goals could not be read. Check desktop Tools.</p>' : '<p>No saved goals for this player. Add one in desktop Tools.</p>')}<h3>Personal records</h3>${details.records.map(r => `<p>${escapeHtml(r.kind)} · ${fmt(r.points)} pts · ${escapeHtml(r.day)}</p>`).join('') || '<p>No recorded improvements.</p>'}<h3>Recent results</h3><div class="history-list">${details.rows.map(r => `<p>${escapeHtml(r.day)} · ${escapeHtml(r.display || r.player)} · ${escapeHtml(r.kind)} · ${fmt(r.points)} pts · Position ${escapeHtml(r.position ?? '—')}</p>`).join('') || '<p>No matching saved results.</p>'}</div>`;
  } catch (_) { if (requestId === detailRequest) el('drawer-content').textContent = 'Details could not be loaded. Close and reopen to retry.'; }
}
function renderPinnedRival(data) {
  let host = el('pinned-rival');
  if (!host) { el('rivals-leaderboard').insertAdjacentHTML('beforebegin','<div id="pinned-rival"></div>'); host = el('pinned-rival'); }
  const rows = data.rivals || [], pinned = readPreference('pinnedRival','');
  host.innerHTML = `<label>Pin matchup <select id="rival-pin"><option value="">Choose a matchup</option>${rows.map(row => `<option value="${escapeHtml(`${row.user_a}|${row.user_b}`)}">${escapeHtml(row.display_a || row.user_a)} / ${escapeHtml(row.display_b || row.user_b)}</option>`).join('')}</select></label><div id="rival-comparison"></div>`;
  el('rival-pin').value = pinned;
  el('rival-pin').onchange = () => { savePreference('pinnedRival',el('rival-pin').value); renderPinnedRival(data); };
  const row = rows.find(r => `${r.user_a}|${r.user_b}` === pinned); if (!row) return;
  // Samples reflect actual dashboard observations, never invented historic points.
  const histories = readPreference('rivalHistory',{}), history = histories[pinned] || [];
  const sample = {at:data.updated_at,gap:Number(row.point_gap || 0)};
  if (!history.length || history[history.length-1].gap !== sample.gap) history.push(sample);
  histories[pinned] = history.slice(-60); savePreference('rivalHistory',histories);
  el('rival-comparison').innerHTML = `<div class="comparison-grid">${['a','b'].map(side => `<article>${playerButton({username:row[`user_${side}`],display_name:row[`display_${side}`]})}${metric('Points',fmt(row[`points_${side}`]))}${metric('Entries',fmt(row[`races_${side}`]))}</article>`).join('')}</div><details><summary>Observed point-gap history (${history.length} samples)</summary><p>Saved in this browser when this pinned matchup changes; earlier history is unavailable.</p>${history.length > 1 ? `<svg class="rival-gap-chart" viewBox="0 0 400 100" role="img" aria-label="Observed point gap"><polyline fill="none" stroke="#63d3ac" stroke-width="3" points="${history.map((x,i) => `${5+i*390/(history.length-1)},${95-x.gap/Math.max(1,...history.map(v=>v.gap))*85}`).join(' ')}"/></svg>` : ''}${history.slice(-60).map(x => `<p>${escapeHtml(x.at)} · Gap ${fmt(x.gap)}</p>`).join('')}</details>`;
}
async function installGuide() {
  guideLoaded = true; // The task guide works even when the optional README.html is absent.
  el('guide-content').innerHTML = `<label>Search guide and commands <input id="guide-search" type="search"></label><div id="guide-tasks"><article data-guide-item><h3>Set up MyStats</h3><p>Select the game export folder in Settings, connect your Twitch channel, and confirm the monitoring status in the desktop Overview.</p></article><article data-guide-item><h3>Add an OBS source</h3><p>Open OBS presets, choose a size and stats, then copy its URL into an OBS Browser Source with the matching width and height.</p></article><article data-guide-item><h3>Control chat</h3><p>Use Settings to choose which game messages are enabled. Desktop Tools lets you pause outgoing chat and preview messages for the current session.</p></article><article data-guide-item><h3>Troubleshoot</h3><p>Check desktop Diagnostics for file monitoring, export paths and recent errors. Run history shows what was saved. A stale banner retains the last successful dashboard while reconnecting.</p></article></div><div id="guide-commands">Loading command reference…</div>`;
  const filter = () => document.querySelectorAll('[data-guide-item]').forEach(item => item.hidden = !item.textContent.toLowerCase().includes(el('guide-search').value.toLowerCase()));
  el('guide-search').oninput = filter;
  try {
    const response = await fetch('/api/dashboard/guide'); if (!response.ok) throw new Error('Unavailable');
    const result = await response.json();
    el('guide-commands').innerHTML = '<h3>Chat commands</h3>' + result.commands.map(c => `<article data-guide-item><strong>${escapeHtml(c.usage || c.name)}</strong><p>${escapeHtml(c.description)}</p><small>${escapeHtml(c.category)}</small></article>`).join(''); filter();
  } catch (_) { el('guide-commands').innerHTML = '<p>Command reference unavailable. Open Help → Commands in the desktop application.</p><button id="retry-guide">Retry</button>'; el('retry-guide').onclick = installGuide; }
}
function installOverlayPresets() {
  const defaults = {name:'Stream card',size:'800x600',opacity:90,scale:110,horizontal:false,stats:'season'};
  const presets = readPreference('overlayPresets',[defaults,{name:'Wide ticker',size:'1920x160',opacity:95,scale:110,horizontal:true,stats:'today'}]);
  el('overlay-presets').innerHTML = `<p>Presets are saved in this browser. Each OBS URL carries its own settings, so sources can use different presentations.</p><div class="shared-controls"><label>Saved preset <select id="preset-select">${presets.map((x,i) => `<option value="${i}">${escapeHtml(x.name)}</option>`).join('')}</select></label><label>Name <input id="preset-name" maxlength="60"></label><label>Target size <select id="preset-size"><option>800x600</option><option>1920x160</option><option>1280x720</option><option>480x800</option></select></label><label>Card opacity <input id="preset-opacity" type="range" min="65" max="100"></label><label>Text scale <input id="preset-scale" type="range" min="80" max="150"></label><label><input id="preset-horizontal" type="checkbox"> Horizontal ticker</label><label>Stats <select id="preset-stats"><option value="season">Season</option><option value="today">Today</option><option value="all">All enabled stats</option></select></label><button id="preset-save">Save preset</button><button id="preset-copy">Copy OBS URL</button></div><p id="preset-status" role="status"></p><input id="preset-url" readonly aria-label="OBS browser source URL"><div class="preset-preview"><iframe id="preset-frame" title="OBS target size preview" loading="lazy"></iframe></div><p>Checkerboard shows transparency. Preview is scaled to fit; set OBS to the target dimensions shown above.</p>`;
  const update = () => {
    const size = el('preset-size').value, [width,height] = size.split('x').map(Number);
    const params = new URLSearchParams({card_opacity:el('preset-opacity').value,text_scale:el('preset-scale').value,horizontal_layout:String(el('preset-horizontal').checked),stats:el('preset-stats').value});
    const url = `${location.origin}/overlay?${params}`;
    el('preset-url').value = url;
    const frame = el('preset-frame'); if (activeView === 'overlays') frame.src = url; frame.width = width; frame.height = height;
    frame.style.width = `${width}px`; frame.style.height = `${height}px`;
    const ratio = Math.min(1, (el('overlay-presets').clientWidth || 600) / width);
    frame.style.transform = `scale(${ratio})`; frame.parentElement.style.height = `${height * ratio}px`;
    el('preset-status').textContent = `OBS source: ${width} × ${height} · Opacity ${el('preset-opacity').value}% · Text ${el('preset-scale').value}%`;
  };
  const load = () => { const x = presets[Number(el('preset-select').value)] || defaults; for (const key of ['name','size','opacity','scale','stats']) el(`preset-${key}`).value = x[key]; el('preset-horizontal').checked = x.horizontal; update(); };
  el('preset-select').onchange = load;
  ['size','opacity','scale','horizontal','stats'].forEach(key => el(`preset-${key}`).onchange = update);
  el('preset-save').onclick = () => {
    const x = {name:el('preset-name').value.trim() || 'My preset',size:el('preset-size').value,opacity:Number(el('preset-opacity').value),scale:Number(el('preset-scale').value),horizontal:el('preset-horizontal').checked,stats:el('preset-stats').value};
    const index = presets.findIndex(p => p.name === x.name); if (index >= 0) presets[index] = x; else presets.push(x);
    savePreference('overlayPresets',presets.slice(-30)); installOverlayPresets(); el('preset-select').value = String(Math.max(0,presets.findIndex(p => p.name === x.name))); el('preset-select').onchange();
  };
  el('preset-copy').onclick = async () => { try { await navigator.clipboard.writeText(el('preset-url').value); el('preset-status').textContent += ' · URL copied'; } catch (_) { el('preset-url').select(); el('preset-status').textContent += ' · Select and copy the URL above'; } };
  load();
}
installDashboardControls();

const requestedView = getRequestedViewFromLocation();
if (requestedView) {
  setActiveView(requestedView);
}

refresh();
wireViewTabs();
wireRaceFilterButtons();
wireTrendControls();
wireTeamFilterButtons();
wireTiltSortControls();
wireSeasonControls();
loadGuideContent();
window.addEventListener('hashchange', () => {
  const hashView = getRequestedViewFromLocation();
  if (hashView) setActiveView(hashView);
});
refreshIntervalHandle = setInterval(refresh, 60000);
startDashboardStream();
