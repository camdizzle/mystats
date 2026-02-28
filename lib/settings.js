const fs = require('fs');
const path = require('path');

function parseSettings(filePath) {
  const out = {};
  if (!fs.existsSync(filePath)) return out;
  for (const line of fs.readFileSync(filePath, 'utf8').split(/\r?\n/)) {
    const i = line.indexOf('=');
    if (i < 1) continue;
    const key = line.slice(0, i).trim();
    const value = line.slice(i + 1).trim();
    if (key) out[key] = value;
  }
  return out;
}

function writeSettings(filePath, settings) {
  const sorted = Object.keys(settings).sort((a, b) => a.localeCompare(b));
  const body = sorted.map((key) => `${key}=${settings[key] ?? ''}`).join('\n') + '\n';
  fs.writeFileSync(filePath, body, 'utf8');
}

function updateSetting(filePath, key, value) {
  const settings = parseSettings(filePath);
  settings[key] = String(value ?? '');
  writeSettings(filePath, settings);
  return settings;
}

function ensureDefaults(filePath, defaults) {
  const settings = parseSettings(filePath);
  let changed = false;
  for (const [k, v] of Object.entries(defaults || {})) {
    if (!(k in settings)) {
      settings[k] = String(v);
      changed = true;
    }
  }
  if (changed) writeSettings(filePath, settings);
  return settings;
}

module.exports = {
  parseSettings,
  writeSettings,
  updateSetting,
  ensureDefaults,
};
