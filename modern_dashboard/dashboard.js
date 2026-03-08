const el = (id) => document.getElementById(id);

let activeView = 'mycycle';
let raceDashboardFilter = 'both';
let tiltSortBy = 'tilt_points';
let tiltSortOrder = 'desc';
let rivalsGuideCollapsed = false;
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
    'Unable to load MyCycle data.': 'No se pudieron cargar los datos de MyCycle.',
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
    'Unable to load MyCycle data.': 'Could not load MyCycle data, bit crook.',
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
          <span class="rank">#${idx + 1 + ((pageInfo?.page || 1) - 1) * (pageInfo?.page_size || rows.length)}</span>
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
          <span class="rank">#${idx + 1}</span>
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
          X
          X
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
  const hardCap = Math.max(1, Number(settings?.max_pairs || 0) || 200);

  return [
    `1) MyStats scans players with at least ${fmt(minRaces)} season races.`,
    `2) It compares point totals and keeps pairs within a ${fmt(maxGap)}-point gap.`,
    `3) The dashboard ranks the ${fmt(Math.min(hardCap, pairCount))} closest pairs (smaller gap = stronger rivalry).`,
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
    contextHost.textContent = t('No rivals currently qualify. Try lowering Minimum Season Races or increasing Maximum Point Gap in Settings → Rivals.');
    return;
  }

  const closest = rows[0];
  const closestNames = `${closest.display_a || closest.user_a || 'Player A'} vs ${closest.display_b || closest.user_b || 'Player B'}`;
  contextHost.textContent = `${t('Current closest rivalry')}: ${closestNames} at ${fmt(closest.point_gap)} points apart.`;
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
  if (incomingRows.length) {
    rivalsRowsSnapshot = incomingRows;
  }
  const rows = getFilteredSortedRivalRows(rivalsRowsSnapshot);
  wireRivalsControls();

  const rivalsSettings = {
    ...(data?.settings?.rivals || {}),
    max_pairs: Number(data?.settings?.rivals_limits?.max_pairs || 200),
  };

  renderRivalsOnboarding(rivalsSettings, rows);
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
    totalLabel: 'Total Events',
    countLabel: 'Events',
    avgLabel: 'Avg Points/Event',
    rowAvgLabel: 'Avg/Event',
  };
}

function renderRaceDashboardKpis(rows = [], filterMode = 'both') {
  const host = el('races-kpis');
  if (!host) return;

  const labels = getRaceFilterLabels(filterMode);
  const filteredRows = rows.filter((row) => getRaceRowTotals(row, filterMode).events > 0);
  const totalEvents = filteredRows.reduce((acc, row) => acc + getRaceRowTotals(row, filterMode).events, 0);
  const totalPoints = filteredRows.reduce((acc, row) => acc + getRaceRowTotals(row, filterMode).points, 0);
  const avgPoints = totalEvents > 0 ? (totalPoints / totalEvents) : 0;

  host.innerHTML = [
    { label: t('Tracked Racers'), value: fmt(filteredRows.length) },
    { label: labels.totalLabel, value: fmt(totalEvents) },
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

  renderRaceDashboardKpis(allRows, raceDashboardFilter);
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
          <span class="rank">#${idx + 1}</span>
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



function buildAnalyticsGroupsMarkup(data) {
  const analytics = data?.analytics || {};
  const groups = analytics?.groups || {};
  const seasonLabel = analytics?.season_label || 'Season';
  const allSeasonsLabel = analytics?.all_seasons_label || 'All Seasons';
  const hasPriorSeasons = Boolean(analytics?.has_prior_seasons);

  const groupOrder = ['race_br_combined', 'tilt', 'race_only', 'br_only', 'mycycle'];
  const metricMap = {
    race_br_combined: [
      ['Races', 'events'], ['Points', 'points'], ['Wins', 'wins'], ['Win Rate %', 'win_rate'], ['Unique Racers', 'unique_racers'],
      ['High Score', 'high_score'], ['PPR', 'ppr'], ['Top PPR Racer', 'top_ppr_name'], ['Top PPR', 'top_ppr'], ['Top PPR Races', 'top_ppr_events'],
    ],
    tilt: [
      ['Participants', 'participants'], ['Tilt Points', 'points'], ['Tilt Levels', 'levels'], ['Top Tiltee Finishes', 'top_tiltee'],
      ['Deaths', 'deaths'], ['Survival Rate %', 'survival_rate'], ['PPR', 'ppr'],
    ],
    race_only: [
      ['Race Count', 'events'], ['Race Points', 'points'], ['Race Wins', 'wins'], ['Win Rate %', 'win_rate'], ['Unique Racers', 'unique_racers'],
      ['Race High Score', 'high_score'], ['Race PPR', 'ppr'], ['Top PPR Racer', 'top_ppr_name'], ['Top PPR', 'top_ppr'], ['Top PPR Races', 'top_ppr_events'],
    ],
    br_only: [
      ['BR Races', 'events'], ['BR Points', 'points'], ['BR Wins', 'wins'], ['Win Rate %', 'win_rate'], ['Unique Racers', 'unique_racers'],
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



function renderSimpleLineChart(title, rows, valueKey, labelKey, formatter = (v) => fmt(v)) {
  if (!Array.isArray(rows) || !rows.length) {
    return `<section class="analytics-group"><h3 class="analytics-group__title">${escapeHtml(title)}</h3><div class="empty">No trend data yet.</div></section>`;
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
    `<circle class="trend-line-dot" cx="${pt.x.toFixed(2)}" cy="${pt.y.toFixed(2)}" r="3.5">
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

  const latestDays = dailyRows.slice(-21);
  const analyticsSection = buildAnalyticsGroupsMarkup(data);

  const charts = [
    analyticsSection.markup,
    renderSimpleLineChart('Unique Racers per Season', seasonSeries, 'unique_racers', 'season_label'),
    renderSimpleLineChart('Total Races per Season', seasonSeries, 'total_races', 'season_label'),
    renderSimpleLineChart('Current Season Daily Unique Racers', latestDays, 'unique_racers', 'date'),
    renderSimpleLineChart('Current Season Daily Total Races', latestDays, 'total_races', 'date'),
    renderSimpleLineChart('Current Season Daily PPR', latestDays, 'ppr', 'date', (v) => Number(v || 0).toFixed(2)),
    renderSimpleLineChart('Current Season Daily BR Count', latestDays, 'br_count', 'date'),
  ];

  chartHost.classList.add('trend-grid');
  chartHost.innerHTML = charts.join('');
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



function getRequestedViewFromLocation() {
  const hashView = String(window.location.hash || '').replace('#', '').trim();
  const validViews = new Set(['mycycle', 'season-quests', 'tilt', 'rivals', 'races', 'trends']);
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

async function refresh() {
  try {
    const params = new URLSearchParams({
      mycycle_page: String(mycyclePage),
      mycycle_page_size: String(mycyclePageSize),
    });
    if (mycycleQuery) params.set('mycycle_query', mycycleQuery);
    if (seasonQuery) params.set('season_query', seasonQuery);
    params.set('season_page', String(seasonPage));
    params.set('season_page_size', String(seasonPageSize));
    params.set('season_sort_by', seasonSortBy);
    params.set('season_sort_order', seasonSortOrder);
    const resp = await fetch(`/api/dashboard/main?${params.toString()}`, { cache: 'no-store' });
    const data = await resp.json();
    currentLanguage = data?.settings?.language || currentLanguage || 'en';
    el('updated-at').textContent = data.updated_at ? `${t('Updated')} ${data.updated_at}` : t('Updated now');
    renderMyCycleRows(data);
    renderSeasonQuestRows(data);
    renderTiltRows(data);
    renderRivalsRows(data);
    renderRaceDashboardRows(data);
    renderRaceTrends(data);
  } catch (error) {
    console.error('dashboard refresh failed', error);
    const fallback = `<div class="empty">${escapeHtml(t('Unable to load MyCycle data.'))}</div>`;
    ['mycycle', 'season-quests', 'tilt-leaderboard', 'rivals-leaderboard', 'races-leaderboard', 'trend-charts'].forEach((id) => {
      const node = el(id);
      if (node) node.innerHTML = fallback;
    });
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
wireSeasonControls();
wireRivalsOnboardingToggle();
window.addEventListener('hashchange', () => {
  const hashView = getRequestedViewFromLocation();
  if (hashView) setActiveView(hashView);
});
setInterval(refresh, 15000);
