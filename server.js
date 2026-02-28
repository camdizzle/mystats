const http = require('http');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');

const ROOT = __dirname;
const SETTINGS_FILE = process.env.MYSTATS_SETTINGS || path.join(ROOT, 'settings.txt');
const DATA_DIR_ENV = process.env.MYSTATS_DATA_DIR;
const MYCYCLE_FILE_NAME = 'mycycle_data.json';
const MYCYCLE_SESSION_PREFIX = 'season_';

function safeInt(value, fallback = 0) {
  if (value == null || value === '') return fallback;
  const normalized = String(value).trim();

  if (/^[+-]?\d{1,3}(?:[.,]\d{3})+$/.test(normalized)) {
    const parsed = Number.parseInt(normalized.replace(/[.,]/g, ''), 10);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  let floatCandidate = normalized;
  if (floatCandidate.includes(',') && !floatCandidate.includes('.')) {
    floatCandidate = floatCandidate.replace(',', '.');
  } else {
    floatCandidate = floatCandidate.replace(/,/g, '');
  }

  const parsed = Number.parseInt(Number.parseFloat(floatCandidate), 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function parseBoolean(value, fallback = false) {
  const v = String(value ?? '').trim().toLowerCase();
  if (['true', '1', 'yes', 'y', 'on'].includes(v)) return true;
  if (['false', '0', 'no', 'n', 'off'].includes(v)) return false;
  return fallback;
}

function parseJsonSafe(raw, fallback) {
  try {
    if (raw == null || raw === '') return fallback;
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}


function writeSettingsFile(nextSettings, filePath = SETTINGS_FILE) {
  const keys = Object.keys(nextSettings || {}).sort((a, b) => a.localeCompare(b));
  const body = keys.map((key) => `${key}=${nextSettings[key] ?? ''}`).join('\n') + '\n';
  fs.writeFileSync(filePath, body, 'utf8');
}

function parseSettings(filePath = SETTINGS_FILE) {
  const out = {};
  if (!fs.existsSync(filePath)) return out;

  for (const line of fs.readFileSync(filePath, 'utf8').split(/\r?\n/)) {
    const idx = line.indexOf('=');
    if (idx < 1) continue;
    const key = line.slice(0, idx).trim();
    const value = line.slice(idx + 1).trim();
    if (key) out[key] = value;
  }
  return out;
}

function parseCsvLine(line) {
  const result = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === ',' && !inQuotes) {
      result.push(current);
      current = '';
    } else {
      current += ch;
    }
  }
  result.push(current);
  return result;
}

function readCsv(filePath) {
  if (!filePath || !fs.existsSync(filePath)) return [];
  return fs.readFileSync(filePath, 'utf8').split(/\r?\n/).filter(Boolean).map(parseCsvLine);
}

function getDataDir(settings) {
  return DATA_DIR_ENV || settings.directory || settings.data_directory || ROOT;
}

function listFilesMatching(dir, regex) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((name) => regex.test(name)).sort().map((name) => path.join(dir, name));
}

function readRaceRows(settings) {
  const dataDir = getDataDir(settings);
  return listFilesMatching(dataDir, /^allraces_.*\.csv$/i)
    .flatMap((file) => readCsv(file).map((row) => ({ row, file })));
}

function parseTiltResultRow(row) {
  if (!Array.isArray(row) || row.length < 5) return null;
  const runId = String(row[0] || '').trim();
  const username = String(row[2] || '').trim();
  if (!username) return null;
  const points = safeInt(row[4], NaN);
  if (!Number.isFinite(points)) return null;
  return { run_id: runId, username, points };
}

function parseTiltResultDetail(row) {
  const parsed = parseTiltResultRow(row);
  if (!parsed) return null;

  const parseFlag = (value, allowNumeric = true) => {
    const token = String(value ?? '').trim().toLowerCase();
    if (['true', 'yes', 'y'].includes(token)) return true;
    if (['false', 'no', 'n'].includes(token)) return false;
    if (allowNumeric && ['1', '0'].includes(token)) return token === '1';
    return null;
  };

  let isTopTiltee = false;
  const tail = row.slice(-6).reverse();
  for (const candidate of tail) {
    const parsedFlag = parseFlag(candidate, false);
    if (parsedFlag !== null) {
      isTopTiltee = parsedFlag;
      break;
    }
  }

  if (!isTopTiltee) {
    for (const candidate of [row[row.length - 1], row[row.length - 2], row[row.length - 3]]) {
      const token = String(candidate ?? '').trim();
      if (!token || token.includes('[') || token.includes(']') || token.includes(',')) continue;
      const parsedFlag = parseFlag(token, true);
      if (parsedFlag !== null) {
        isTopTiltee = parsedFlag;
        break;
      }
    }
  }

  return {
    run_id: parsed.run_id,
    username: parsed.username,
    points: parsed.points,
    is_top_tiltee: isTopTiltee,
  };
}

function getTiltSeasonStats(settings) {
  const dataDir = getDataDir(settings);
  const files = listFilesMatching(dataDir, /^tilts_.*\.csv$/i);

  const totals = { levels: 0, top_tiltees: 0, points: 0 };
  const users = new Map();

  for (const file of files) {
    for (const row of readCsv(file)) {
      const detail = parseTiltResultDetail(row);
      if (!detail) continue;

      const username = detail.username.toLowerCase();
      const current = users.get(username) || {
        display_name: detail.username,
        tilt_levels: 0,
        tilt_top_tiltee: 0,
        tilt_points: 0,
      };

      current.tilt_levels += 1;
      current.tilt_points += detail.points;
      totals.levels += 1;
      totals.points += detail.points;

      if (detail.is_top_tiltee) {
        current.tilt_top_tiltee += 1;
        totals.top_tiltees += 1;
      }

      users.set(username, current);
    }
  }

  return { totals, users };
}

function getUserSeasonStats(settings) {
  const users = new Map();

  for (const { row } of readRaceRows(settings)) {
    if (!Array.isArray(row) || row.length < 5) continue;

    const username = String(row[1] || '').trim().toLowerCase();
    if (!username) continue;

    const displayName = String(row[2] || '').trim() || username;
    const points = safeInt(row[3], 0);
    const mode = String(row[4] || '').trim().toLowerCase();

    const current = users.get(username) || {
      display_name: displayName,
      races: 0,
      points: 0,
      race_hs: 0,
      br_hs: 0,
      tilt_levels: 0,
      tilt_top_tiltee: 0,
      tilt_points: 0,
    };

    current.display_name = displayName || current.display_name;
    current.races += 1;
    current.points += points;
    if (mode === 'race') current.race_hs = Math.max(current.race_hs, points);
    if (mode === 'br') current.br_hs = Math.max(current.br_hs, points);

    users.set(username, current);
  }

  const tilt = getTiltSeasonStats(settings);
  for (const [username, tiltStats] of tilt.users.entries()) {
    const current = users.get(username) || {
      display_name: tiltStats.display_name || username,
      races: 0,
      points: 0,
      race_hs: 0,
      br_hs: 0,
      tilt_levels: 0,
      tilt_top_tiltee: 0,
      tilt_points: 0,
    };

    current.tilt_levels += tiltStats.tilt_levels || 0;
    current.tilt_top_tiltee += tiltStats.tilt_top_tiltee || 0;
    current.tilt_points += tiltStats.tilt_points || 0;
    if (!current.display_name) current.display_name = tiltStats.display_name || username;
    users.set(username, current);
  }

  return users;
}

function getSeasonQuestTargets(settings) {
  return {
    races: safeInt(settings.season_quest_target_races, 0),
    points: safeInt(settings.season_quest_target_points, 0),
    race_hs: safeInt(settings.season_quest_target_race_hs, 0),
    br_hs: safeInt(settings.season_quest_target_br_hs, 0),
    tilt_levels: safeInt(settings.season_quest_target_tilt_levels, 0),
    tilt_tops: safeInt(settings.season_quest_target_tilt_tops, 0),
    tilt_points: safeInt(settings.season_quest_target_tilt_points, 0),
  };
}

function getQuestCompletionLeaderboard(settings, limit = 100) {
  const userStats = getUserSeasonStats(settings);
  const targets = getSeasonQuestTargets(settings);

  const leaderboard = [...userStats.entries()].map(([username, stats]) => {
    const checks = [
      ['races', stats.races],
      ['points', stats.points],
      ['race_hs', stats.race_hs],
      ['br_hs', stats.br_hs],
      ['tilt_levels', stats.tilt_levels || 0],
      ['tilt_tops', stats.tilt_top_tiltee || 0],
      ['tilt_points', stats.tilt_points || 0],
    ];

    let completed = 0;
    let active_quests = 0;

    for (const [key, value] of checks) {
      const target = safeInt(targets[key], 0);
      if (target <= 0) continue;
      active_quests += 1;
      if (value >= target) completed += 1;
    }

    return {
      username,
      display_name: stats.display_name || username,
      completed: active_quests > 0 ? completed : 0,
      active_quests,
      races: stats.races,
      points: stats.points,
      race_hs: stats.race_hs,
      br_hs: stats.br_hs,
      tilt_levels: stats.tilt_levels || 0,
      tilt_top_tiltee: stats.tilt_top_tiltee || 0,
      tilt_points: stats.tilt_points || 0,
    };
  });

  return leaderboard.sort((a, b) => {
    if (b.completed !== a.completed) return b.completed - a.completed;
    if (b.points !== a.points) return b.points - a.points;
    return b.races - a.races;
  }).slice(0, limit);
}

function getRivalSettings(settings) {
  return {
    min_races: Math.max(1, safeInt(settings.rivals_min_races, 50)),
    max_point_gap: Math.max(0, safeInt(settings.rivals_max_point_gap, 1500)),
    pair_count: Math.max(1, safeInt(settings.rivals_pair_count, 25)),
  };
}

function getGlobalRivalries(settings, limit = null) {
  const userStats = getUserSeasonStats(settings);
  const rivalSettings = getRivalSettings(settings);

  const qualified = [...userStats.entries()].filter(([, stats]) => stats.races >= rivalSettings.min_races && stats.points > 0);

  const rivalries = [];
  for (let i = 0; i < qualified.length; i += 1) {
    const [userA, statsA] = qualified[i];
    for (let j = i + 1; j < qualified.length; j += 1) {
      const [userB, statsB] = qualified[j];
      const gap = Math.abs(statsA.points - statsB.points);
      if (gap > rivalSettings.max_point_gap) continue;

      rivalries.push({
        user_a: userA,
        display_a: statsA.display_name || userA,
        points_a: statsA.points || 0,
        races_a: statsA.races || 0,
        user_b: userB,
        display_b: statsB.display_name || userB,
        points_b: statsB.points || 0,
        races_b: statsB.races || 0,
        point_gap: gap,
      });
    }
  }

  const cap = limit == null ? rivalSettings.pair_count : limit;
  return rivalries.sort((a, b) => (a.point_gap - b.point_gap) || ((b.points_a + b.points_b) - (a.points_a + a.points_b))).slice(0, cap);
}

function getMycycleSettings(settings) {
  let minPlace = Math.max(1, safeInt(settings.mycycle_min_place, 1));
  let maxPlace = Math.max(1, safeInt(settings.mycycle_max_place, 10));
  if (minPlace > maxPlace) {
    minPlace = 1;
    maxPlace = 10;
  }

  return {
    enabled: parseBoolean(settings.mycycle_enabled, false),
    announce: parseBoolean(settings.mycycle_announcements_enabled, false),
    include_br: parseBoolean(settings.mycycle_include_br, false),
    min_place: minPlace,
    max_place: maxPlace,
  };
}

function mycycleFilePath(settings) {
  return path.join(getDataDir(settings), MYCYCLE_FILE_NAME);
}

function loadMycycleData(settings) {
  const filePath = mycycleFilePath(settings);
  if (!fs.existsSync(filePath)) return { version: 1, sessions: {} };
  const parsed = parseJsonSafe(fs.readFileSync(filePath, 'utf8'), { version: 1, sessions: {} });
  if (!parsed || typeof parsed !== 'object') return { version: 1, sessions: {} };
  parsed.version = parsed.version || 1;
  parsed.sessions = parsed.sessions || {};
  return parsed;
}

function ensureDefaultMycycleSession(settings, data) {
  const season = String(settings.season || 'unknown');
  const sessionId = `${MYCYCLE_SESSION_PREFIX}${season}`;

  data.sessions = data.sessions || {};
  if (!data.sessions[sessionId]) {
    data.sessions[sessionId] = {
      id: sessionId,
      name: `Season ${season}`,
      season,
      active: true,
      is_default: true,
      created_at: new Date().toISOString().slice(0, 19).replace('T', ' '),
      created_by: 'system',
      stats: {},
    };
  }
  return sessionId;
}

function getMycycleHomeSessionIds(settings, data) {
  const defaultId = ensureDefaultMycycleSession(settings, data);
  const activeSessions = Object.values(data.sessions).filter((session) => session.active !== false);
  if (!activeSessions.length) return { sessionIds: [], preferred: null };

  const preferred = String(settings.mycycle_primary_session_id || defaultId);
  const ids = activeSessions.map((session) => session.id);
  const first = ids.includes(preferred) ? preferred : ids[0];

  return { sessionIds: [first, ...ids.filter((id) => id !== first)], preferred: first };
}

function getMycycleLeaderboard(settings, limit = 250) {
  const data = loadMycycleData(settings);
  const { sessionIds } = getMycycleHomeSessionIds(settings, data);
  const sessionId = sessionIds[0] || ensureDefaultMycycleSession(settings, data);
  const session = data.sessions[sessionId] || { id: sessionId, name: sessionId, stats: {} };
  const stats = session.stats || {};
  const cycleSettings = getMycycleSettings(settings);

  const placementRange = [];
  for (let place = cycleSettings.min_place; place <= cycleSettings.max_place; place += 1) {
    placementRange.push(place);
  }

  const leaderboard = Object.entries(stats).map(([username, row]) => {
    const hits = new Set((Array.isArray(row.current_hits) ? row.current_hits : []).map((value) => safeInt(value, 0)).filter((value) => value > 0));
    const missingPlaces = placementRange.filter((place) => !hits.has(place));
    const progressTotal = Math.max(1, cycleSettings.max_place - cycleSettings.min_place + 1);
    const progressHits = hits.size;

    return {
      username,
      display_name: row.display_name || username,
      cycles_completed: safeInt(row.cycles_completed, 0),
      progress_hits: progressHits,
      progress_total: progressTotal,
      progress_percent: Number(((progressHits / progressTotal) * 100).toFixed(1)),
      placement_hits: [...hits].sort((a, b) => a - b),
      missing_places: missingPlaces,
      current_cycle_races: safeInt(row.current_cycle_races, 0),
      last_cycle_races: safeInt(row.last_cycle_races, 0),
      last_cycle_completed_at: row.last_cycle_completed_at || null,
    };
  }).sort((a, b) => {
    if (b.cycles_completed !== a.cycles_completed) return b.cycles_completed - a.cycles_completed;
    if (b.progress_hits !== a.progress_hits) return b.progress_hits - a.progress_hits;
    return a.current_cycle_races - b.current_cycle_races;
  }).slice(0, limit);

  return { session, rows: leaderboard, settings: cycleSettings };
}

function buildOverlaySettings(settings) {
  return {
    rotation_seconds: safeInt(settings.overlay_rotation_seconds, 10) || 10,
    refresh_seconds: safeInt(settings.overlay_refresh_seconds, 3) || 3,
    theme: String(settings.overlay_theme || 'midnight').toLowerCase(),
    card_opacity: safeInt(settings.overlay_card_opacity, 84) || 84,
    text_scale: safeInt(settings.overlay_text_scale, 100) || 100,
    show_medals: String(settings.overlay_show_medals || 'True'),
    compact_rows: String(settings.overlay_compact_rows || 'False'),
    horizontal_layout: String(settings.overlay_horizontal_layout || 'False'),
    tilt_theme: String(settings.tilt_overlay_theme || settings.overlay_theme || 'midnight').toLowerCase(),
    tilt_scroll_step_px: safeInt(settings.tilt_scroll_step_px, 1) || 1,
    tilt_scroll_interval_ms: safeInt(settings.tilt_scroll_interval_ms, 40) || 40,
    tilt_scroll_pause_ms: safeInt(settings.tilt_scroll_pause_ms, 900) || 900,
    language: String(settings.app_language || 'en').toLowerCase(),
  };
}

function top10ByPoints(files) {
  const users = new Map();
  for (const file of files) {
    for (const row of readCsv(file)) {
      if (row.length < 5) continue;
      const username = String(row[1] || '').trim().toLowerCase();
      if (!username) continue;
      const display = String(row[2] || row[1] || '').trim();
      const points = safeInt(row[3], 0);
      const current = users.get(username) || { username, name: display || username, points: 0 };
      current.points += points;
      if (display) current.name = display;
      users.set(username, current);
    }
  }
  return [...users.values()]
    .sort((a, b) => (b.points - a.points) || a.name.localeCompare(b.name))
    .slice(0, 10)
    .map((row, index) => ({ placement: index + 1, name: row.name, points: row.points, finished: true }));
}

function buildHeaderStats(settings) {
  const files = listFilesMatching(getDataDir(settings), /^allraces_.*\.csv$/i);

  const calculate = (targetFiles) => {
    const state = { points: 0, entries: 0, races: 0, unique: new Set() };
    for (const file of targetFiles) {
      for (const row of readCsv(file)) {
        if (row.length < 5) continue;
        const racer = String(row[2] || row[1] || '').trim();
        if (racer) state.unique.add(racer.toLowerCase());
        const points = safeInt(row[3], 0);
        if (!points || !racer) continue;
        state.points += points;
        state.entries += 1;
        if (safeInt(String(row[0] || '').replace(/\D+/g, ''), 0) === 1) state.races += 1;
      }
    }
    return state;
  };

  const season = calculate(files);
  const todayFile = settings.allraces_file && fs.existsSync(settings.allraces_file)
    ? settings.allraces_file
    : files[files.length - 1];
  const today = calculate(todayFile ? [todayFile] : []);

  return {
    avg_points_today: today.entries ? Number((today.points / today.entries).toFixed(2)) : 0,
    avg_points_season: season.entries ? Number((season.points / season.entries).toFixed(2)) : 0,
    unique_racers_today: today.unique.size,
    unique_racers_season: season.unique.size,
    total_races_today: today.races,
    total_races_season: season.races,
  };
}

function buildRecentRaceTop3(todayFile) {
  const rows = readCsv(todayFile);
  if (!rows.length) return null;

  const raceRows = rows
    .map((row) => ({
      placement: safeInt(String(row[0] || '').replace(/\D+/g, ''), 0),
      name: String(row[2] || row[1] || '').trim() || 'Unknown Racer',
      points: safeInt(row[3], 0),
      finished: true,
    }))
    .filter((row) => row.placement > 0)
    .sort((a, b) => a.placement - b.placement)
    .slice(0, 3);

  if (!raceRows.length) return null;

  return {
    race_key: `race-${rows.length}`,
    title: '🔥 Latest Race Podium 🔥',
    rows: raceRows,
    is_record_race: false,
    record_holder_name: '',
    record_delta_seconds: 0,
  };
}

function getRaceDashboardLeaderboard(settings, limit = 250) {
  const users = new Map();

  for (const { row } of readRaceRows(settings)) {
    if (row.length < 5) continue;

    const username = String(row[1] || '').trim().toLowerCase();
    if (!username) continue;

    const displayName = String(row[2] || '').trim() || username;
    const mode = String(row[4] || '').trim().toLowerCase();
    const points = safeInt(row[3], 0);

    const current = users.get(username) || {
      username,
      display_name: displayName,
      race_count: 0,
      br_count: 0,
      race_points: 0,
      br_points: 0,
      race_hs: 0,
      br_hs: 0,
    };

    current.display_name = displayName || current.display_name;
    if (mode === 'race') {
      current.race_count += 1;
      current.race_points += points;
      current.race_hs = Math.max(current.race_hs, points);
    } else if (mode === 'br') {
      current.br_count += 1;
      current.br_points += points;
      current.br_hs = Math.max(current.br_hs, points);
    }

    users.set(username, current);
  }

  return [...users.values()]
    .map((row) => {
      const total_events = row.race_count + row.br_count;
      const total_points = row.race_points + row.br_points;
      return {
        ...row,
        total_events,
        total_points,
        avg_points: total_events > 0 ? Number((total_points / total_events).toFixed(2)) : 0,
      };
    })
    .sort((a, b) => {
      if (b.total_points !== a.total_points) return b.total_points - a.total_points;
      if (b.total_events !== a.total_events) return b.total_events - a.total_events;
      if (b.race_hs !== a.race_hs) return b.race_hs - a.race_hs;
      return b.br_hs - a.br_hs;
    })
    .slice(0, limit);
}

function buildMainDashboardPayload(settings) {
  const mycycle = getMycycleLeaderboard(settings, 250);
  const seasonRows = getQuestCompletionLeaderboard(settings, 100);
  const seasonTargets = getSeasonQuestTargets(settings);
  const tilt = getTiltSeasonStats(settings);

  return {
    updated_at: new Date().toISOString(),
    season_quests: {
      rows: seasonRows,
      targets: seasonTargets,
    },
    season_quest_targets: seasonTargets,
    rivals: getGlobalRivalries(settings, 200),
    races: getRaceDashboardLeaderboard(settings, 250),
    mycycle,
    tilt: {
      totals: tilt.totals,
      deaths_today: safeInt(settings.tilt_total_deaths_today, 0),
      participants: tilt.users.size,
    },
    settings: {
      language: String(settings.app_language || 'en').toLowerCase(),
    },
  };
}

function buildTiltOverlayPayload(settings) {
  const currentRunId = String(settings.tilt_current_run_id || '').trim();
  const standings = parseJsonSafe(settings.tilt_current_run_standings, []);

  return {
    updated_at: new Date().toISOString(),
    title: 'MyStats Tilt Run Tracker',
    settings: {
      ...buildOverlaySettings(settings),
      theme: String(settings.tilt_overlay_theme || settings.overlay_theme || 'midnight').toLowerCase(),
    },
    current_run: {
      run_id: currentRunId,
      run_short_id: currentRunId.slice(0, 6),
      status: currentRunId ? 'active' : 'idle',
      level: safeInt(settings.tilt_current_level, 0),
      elapsed_time: String(settings.tilt_current_elapsed || '0:00'),
      top_tiltee: String(settings.tilt_current_top_tiltee || 'None'),
      top_tiltee_count: safeInt(settings.tilt_current_top_tiltee_count, 0),
      run_points: safeInt(settings.tilt_run_points, 0),
      run_xp: safeInt(settings.tilt_run_xp, 0),
      best_run_xp_today: safeInt(settings.tilt_best_run_xp_today, 0),
      total_xp_today: safeInt(settings.tilt_total_xp_today, 0),
      total_deaths_today: safeInt(settings.tilt_total_deaths_today, 0),
      lifetime_expertise: safeInt(settings.tilt_lifetime_expertise, 0),
      standings,
      leader: Array.isArray(standings) && standings[0] ? standings[0] : null,
    },
    last_run: parseJsonSafe(settings.tilt_last_run_summary, {}),
    level_completion: parseJsonSafe(settings.tilt_level_completion_overlay, {}),
    run_completion: parseJsonSafe(settings.tilt_run_completion_overlay, {}),
    run_completion_event_id: safeInt(settings.tilt_run_completion_event_id, 0),
    suppress_initial_recaps: true,
  };
}

function sendJson(res, payload) {
  res.writeHead(200, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
  });
  res.end(JSON.stringify(payload));
}

function sendFile(res, filePath) {
  if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('Not Found');
    return;
  }

  const ext = path.extname(filePath).toLowerCase();
  const mime = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.json': 'application/json; charset=utf-8',
  }[ext] || 'application/octet-stream';

  res.writeHead(200, {
    'Content-Type': mime,
    'Cache-Control': 'no-store',
  });
  res.end(fs.readFileSync(filePath));
}

function safeJoin(baseDir, requestedPath) {
  const resolved = path.resolve(baseDir, requestedPath);
  if (!resolved.startsWith(path.resolve(baseDir))) return null;
  return resolved;
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');
  const pathname = url.pathname;
  const settings = parseSettings();

  if (pathname === '/') {
    res.writeHead(302, { Location: '/dashboard' });
    res.end();
    return;
  }

  if (pathname === '/dashboard') return sendFile(res, path.join(ROOT, 'modern_dashboard', 'index.html'));
  if (pathname === '/overlay') return sendFile(res, path.join(ROOT, 'obs_overlay', 'index.html'));
  if (pathname === '/overlay/tilt') return sendFile(res, path.join(ROOT, 'obs_overlay', 'tilt.html'));

  if (pathname.startsWith('/dashboard/')) {
    const local = safeJoin(path.join(ROOT, 'modern_dashboard'), pathname.replace('/dashboard/', ''));
    if (!local) {
      res.writeHead(400);
      res.end('Bad Request');
      return;
    }
    return sendFile(res, local);
  }

  if (pathname.startsWith('/overlay/')) {
    const local = safeJoin(path.join(ROOT, 'obs_overlay'), pathname.replace('/overlay/', ''));
    if (!local) {
      res.writeHead(400);
      res.end('Bad Request');
      return;
    }
    return sendFile(res, local);
  }

  if (pathname === '/api/overlay/settings') return sendJson(res, buildOverlaySettings(settings));

  if (pathname === '/api/overlay/top3') {
    const allRaceFiles = listFilesMatching(getDataDir(settings), /^allraces_.*\.csv$/i);
    const todayFile = settings.allraces_file && fs.existsSync(settings.allraces_file)
      ? settings.allraces_file
      : allRaceFiles[allRaceFiles.length - 1];

    const seasonRows = top10ByPoints(allRaceFiles);
    const todayRows = top10ByPoints(todayFile ? [todayFile] : []);

    return sendJson(res, {
      updated_at: new Date().toISOString(),
      title: 'MyStats Live Results',
      settings: buildOverlaySettings(settings),
      header_stats: buildHeaderStats(settings),
      top10_season: seasonRows,
      top10_today: todayRows,
      recent_race_top3: todayFile ? buildRecentRaceTop3(todayFile) : null,
      views: [
        { id: 'season', title: 'Top 10 Season', rows: seasonRows },
        { id: 'today', title: 'Top 10 Today', rows: todayRows },
      ],
    });
  }

  if (pathname === '/api/overlay/tilt') return sendJson(res, buildTiltOverlayPayload(settings));
  if (pathname === '/api/dashboard/main') return sendJson(res, buildMainDashboardPayload(settings));

  if (pathname === '/desktop-preview') return sendFile(res, path.join(ROOT, 'desktop_app', 'index.html'));
  if (pathname.startsWith('/desktop-preview/')) {
    const local = safeJoin(path.join(ROOT, 'desktop_app'), pathname.replace('/desktop-preview/', ''));
    if (!local) {
      res.writeHead(400);
      res.end('Bad Request');
      return;
    }
    return sendFile(res, local);
  }

  if (pathname === '/app') return sendFile(res, path.join(ROOT, 'desktop_ui', 'index.html'));
  if (pathname.startsWith('/app/')) {
    const local = safeJoin(path.join(ROOT, 'desktop_ui'), pathname.replace('/app/', ''));
    if (!local) {
      res.writeHead(400);
      res.end('Bad Request');
      return;
    }
    return sendFile(res, local);
  }

  if (pathname === '/api/settings' && req.method === 'GET') {
    return sendJson(res, { settings });
  }

  if (pathname === '/api/settings' && req.method === 'POST') {
    let body = '';
    req.on('data', (chunk) => { body += chunk.toString('utf8'); });
    req.on('end', () => {
      const parsed = parseJsonSafe(body, {});
      if (!parsed || typeof parsed !== 'object') {
        res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ error: 'invalid_json' }));
        return;
      }

      const merged = { ...settings };
      for (const [key, value] of Object.entries(parsed)) {
        if (value == null) continue;
        merged[String(key)] = String(value);
      }
      writeSettingsFile(merged);
      return sendJson(res, { ok: true, settings: merged });
    });
    return;
  }

  res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('Not Found');
});

function startServer(customPort = null) {
  const initialSettings = parseSettings();
  const port = customPort == null
    ? (safeInt(initialSettings.overlay_server_port, safeInt(process.env.PORT, 5000)) || 5000)
    : customPort;

  server.listen(port, '0.0.0.0', () => {
    console.log(`MyStats Node server running at http://127.0.0.1:${port}`);
  });
  return { server, port };
}

module.exports = {
  startServer,
  buildMainDashboardPayload,
  buildTiltOverlayPayload,
  buildOverlaySettings,
};

if (require.main === module) {
  startServer();
}
