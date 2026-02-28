const desktopApi = window.mystatsDesktop || {
  getBootstrap: async () => {
    const settingsResp = await fetch('/api/settings', { cache: 'no-store' });
    const settingsPayload = await settingsResp.json();
    return { settings: settingsPayload.settings || {}, port: Number((settingsPayload.settings || {}).overlay_server_port || 5000), logs: [] };
  },
  saveSettings: async (payload) => {
    const resp = await fetch('/api/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload || {}) });
    const out = await resp.json();
    return out.settings || {};
  },
  botStart: async () => false,
  botStop: async () => false,
  botSay: async () => false,
  openUrl: async (url) => { window.open(url, '_blank'); return true; },
  onLog: () => {},
};

const tabsBySection = {
  General: ['CHANNEL', 'season', 'marble_day', 'directory', 'app_language'],
  Audio: ['audio_enabled', 'audio_volume', 'win_sound_file'],
  Chat: ['TWITCH_USERNAME', 'TWITCH_OAUTH', 'chat_enabled'],
  'Season Quests': ['season_quest_target_races', 'season_quest_target_points', 'season_quest_target_race_hs', 'season_quest_target_br_hs', 'season_quest_target_tilt_levels', 'season_quest_target_tilt_tops', 'season_quest_target_tilt_points'],
  Rivals: ['rivals_min_races', 'rivals_max_point_gap', 'rivals_pair_count'],
  MyCycle: ['mycycle_enabled', 'mycycle_announcements_enabled', 'mycycle_include_br', 'mycycle_min_place', 'mycycle_max_place'],
  Appearance: ['ui_theme', 'overlay_text_scale'],
  Overlay: ['overlay_server_port', 'overlay_rotation_seconds', 'overlay_refresh_seconds', 'overlay_theme', 'overlay_card_opacity', 'overlay_show_medals', 'overlay_compact_rows', 'overlay_horizontal_layout'],
  Tilt: ['tilt_overlay_theme', 'tilt_scroll_step_px', 'tilt_scroll_interval_ms', 'tilt_scroll_pause_ms', 'tilt_total_deaths_today'],
};

let settings = {};
let currentSection = 'General';
let port = 5000;

const $ = (id) => document.getElementById(id);

function addLog(line) {
  const el = $('console');
  el.textContent += `${line}\n`;
  el.scrollTop = el.scrollHeight;
}

function renderTabs() {
  const host = $('tabs');
  host.innerHTML = Object.keys(tabsBySection).map((name) => `<button class="tab ${name === currentSection ? 'active' : ''}" data-name="${name}">${name}</button>`).join('');
  host.querySelectorAll('button').forEach((btn) => btn.addEventListener('click', () => {
    currentSection = btn.dataset.name;
    renderTabs();
    renderFields();
  }));
}

function renderFields() {
  $('section-title').textContent = currentSection;
  const host = $('fields');
  host.innerHTML = (tabsBySection[currentSection] || []).map((key) => `
    <label>${key}<input data-key="${key}" value="${String(settings[key] ?? '').replace(/"/g, '&quot;')}" /></label>
  `).join('');
}

function collectFields() {
  const out = { ...settings };
  document.querySelectorAll('#fields input[data-key]').forEach((input) => {
    out[input.dataset.key] = input.value;
  });
  return out;
}

async function refreshSummary() {
  try {
    const resp = await fetch(`http://127.0.0.1:${port}/api/dashboard/main`, { cache: 'no-store' });
    const p = await resp.json();
    const racers = Array.isArray(p?.races) ? p.races.length : 0;
    const rivals = Array.isArray(p?.rivals) ? p.rivals.length : 0;
    const mycycle = Array.isArray(p?.mycycle?.rows) ? p.mycycle.rows.length : 0;
    $('summary').textContent = `Tracked racers: ${racers} | Rivals: ${rivals} | MyCycle entries: ${mycycle}`;
  } catch (e) {
    $('summary').textContent = 'Unable to load summary.';
  }
}

async function bootstrap() {
  const data = await desktopApi.getBootstrap();
  settings = data.settings || {};
  port = Number(settings.overlay_server_port || data.port || 5000);

  renderTabs();
  renderFields();
  (data.logs || []).forEach(addLog);
  refreshSummary();
}

desktopApi.onLog((line) => addLog(line));

$('save-settings').addEventListener('click', async () => {
  settings = await desktopApi.saveSettings(collectFields());
  addLog('Settings saved.');
  renderFields();
  refreshSummary();
});

$('bot-start').addEventListener('click', async () => { await desktopApi.botStart(); });
$('bot-stop').addEventListener('click', async () => { await desktopApi.botStop(); });
$('bot-say').addEventListener('click', async () => {
  const msg = $('chat-message').value.trim();
  if (!msg) return;
  await desktopApi.botSay(msg);
  $('chat-message').value = '';
});
$('open-dashboard').addEventListener('click', () => desktopApi.openUrl(`http://127.0.0.1:${port}/dashboard`));
$('open-overlay').addEventListener('click', () => desktopApi.openUrl(`http://127.0.0.1:${port}/overlay`));
$('open-tilt').addEventListener('click', () => desktopApi.openUrl(`http://127.0.0.1:${port}/overlay/tilt`));

bootstrap().catch((e) => addLog(`Bootstrap error: ${e.message}`));
